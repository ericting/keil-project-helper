import os
import xml.etree.ElementTree as ET
from pathlib import Path

class KeilProjectManager:
    def __init__(self, project_file):
        self.project_file = project_file
        self.project_dir = os.path.dirname(os.path.abspath(project_file))
        self.tree = ET.parse(project_file)
        self.root = self.tree.getroot()
        
    def get_relative_path(self, absolute_path):
        """获取相对于项目文件的路径"""
        abs_path = os.path.abspath(absolute_path)
        rel_path = os.path.relpath(abs_path, self.project_dir)
        return '../' + rel_path if not rel_path.startswith('..') else rel_path
        
    def find_include_path_node(self):
        """找到Include路径节点"""
        cads = self.root.find('.//Cads')
        if cads is None:
            return None
        various_controls = cads.find('VariousControls')
        if various_controls is None:
            return None
        include_path = various_controls.find('IncludePath')
        if include_path is None:
            include_path = ET.SubElement(various_controls, 'IncludePath')
        return include_path
        
    def add_include_path(self, folder_path):
        """添加Include路径"""
        include_path_node = self.find_include_path_node()
        if include_path_node is None:
            return
            
        # 获取相对路径
        rel_path = self.get_relative_path(folder_path)
        
        # 添加到现有Include路径
        current_paths = include_path_node.text.split(';') if include_path_node.text else []
        if rel_path not in current_paths:
            current_paths.append(rel_path)
            include_path_node.text = ';'.join(filter(None, current_paths))
            
    def add_file(self, file_path, group):
        """添加文件到分组"""
        files = group.find('Files')
        if files is None:
            files = ET.SubElement(group, 'Files')
            
        # 使用相对路径
        rel_path = self.get_relative_path(file_path)
        
        file_elem = ET.SubElement(files, 'File')
        file_name = ET.SubElement(file_elem, 'FileName')
        file_name.text = os.path.basename(file_path)
        
        # 根据文件扩展名设置文件类型
        ext = os.path.splitext(file_path)[1].lower()
        if ext in ['.c']:
            file_type = '1'  # C源文件
        elif ext in ['.cpp']:
            file_type = '8'  # C++源文件
        elif ext in ['.h', '.hpp']:
            file_type = '5'  # 头文件
        elif ext in ['.s']:
            file_type = '2'  # 汇编源文件
        elif ext in ['.lib']:
            file_type = '4'  # 库文件
        elif ext in ['.a']:
            file_type = '4'  # 静态库文件        
        else:
            file_type = '1'  # 默认为C源文件
        
        file_type_elem = ET.SubElement(file_elem, 'FileType')
        file_type_elem.text = file_type
        
        file_path_elem = ET.SubElement(file_elem, 'FilePath')
        file_path_elem.text = rel_path
        
    def scan_and_add_files(self, folder_path):
        """扫描文件夹并添加文件"""
        folder_path = Path(folder_path)
        groups_node = self.root.find('.//Groups')
        if groups_node is None:
            return
            
        # 添加基础Include路径
        self.add_include_path(str(folder_path))
        
        # 遍历文件夹
        for root, dirs, files in os.walk(folder_path):
            current_path = Path(root)
            relative_path = current_path.relative_to(folder_path)
            
            # 构建组名
            if str(relative_path) == '.':
                group_name = folder_path.name
            else:
                group_name = f"{folder_path.name}/{str(relative_path).replace(os.sep, '/')}"
                
            # 检查是否有.c文件
            # source_files = [f for f in files if f.endswith('.c')]
            # 增加其他文件类型支持 .c .cpp .h .hpp .s
            source_files = [f for f in files if f.endswith(('.c', '.cpp', '.h', '.hpp', '.s'))]
            if not source_files:
                continue
                
            # 创建组
            group = ET.SubElement(groups_node, 'Group')
            group_name_elem = ET.SubElement(group, 'GroupName')
            group_name_elem.text = group_name
            
            # 添加文件
            for c_file in source_files:
                file_path = os.path.join(root, c_file)
                self.add_file(file_path, group)
                
            # 添加Include路径
            self.add_include_path(root)
                
    def save(self):
        """保存工程文件"""
        self.tree.write(self.project_file, encoding='utf-8', xml_declaration=True)

def main():
    # 使用示例
    project_file = "./Project/BootUpdateXIP.uvprojx"
    folder_to_add = "./Source/Test"
    
    manager = KeilProjectManager(project_file)
    manager.scan_and_add_files(folder_to_add)
    manager.save()

if __name__ == "__main__":
    main()