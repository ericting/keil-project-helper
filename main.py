import os
import xml.etree.ElementTree as ET
from pathlib import Path
import argparse
import sys

class KeilProjectManager:
    def __init__(self, project_file):
        self.project_file = os.path.abspath(project_file)
        self.project_dir = os.path.dirname(self.project_file)
        try:
            self.tree = ET.parse(project_file)
            self.root = self.tree.getroot()
        except Exception as e:
            print(f"错误：无法解析项目文件 {project_file}，原因：{str(e)}")
            sys.exit(1)
        
    def get_relative_path(self, absolute_path):
        """获取相对于项目文件的路径"""
        try:
            abs_path = os.path.abspath(absolute_path)
            rel_path = os.path.relpath(abs_path, self.project_dir)
            
            # 根据Keil的路径规则处理
            # 如果路径不是以..开头，则添加../
            if not rel_path.startswith('..') and not rel_path.startswith('./'):
                return './' + rel_path
            return rel_path
        except Exception as e:
            print(f"警告：计算路径 {absolute_path} 相对于 {self.project_dir} 的相对路径时出错：{str(e)}")
            return absolute_path
    
    def find_all_targets(self):
        """找到项目中的所有Target"""
        targets = []
        for target in self.root.findall('.//Target'):
            target_name = target.find('TargetName')
            if target_name is not None:
                targets.append((target, target_name.text))
        return targets
    
    def find_include_path_node_for_target(self, target):
        """为特定Target找到Include路径节点"""
        cads = target.find('.//Cads')
        if cads is None:
            return None
        various_controls = cads.find('VariousControls')
        if various_controls is None:
            various_controls = ET.SubElement(cads, 'VariousControls')
        include_path = various_controls.find('IncludePath')
        if include_path is None:
            include_path = ET.SubElement(various_controls, 'IncludePath')
        return include_path
        
    def find_include_path_node(self):
        """找到默认Target的Include路径节点（向后兼容）"""
        cads = self.root.find('.//Cads')
        if cads is None:
            print("警告：未找到Cads节点")
            return None
        various_controls = cads.find('VariousControls')
        if various_controls is None:
            print("警告：未找到VariousControls节点，尝试创建")
            various_controls = ET.SubElement(cads, 'VariousControls')
        include_path = various_controls.find('IncludePath')
        if include_path is None:
            print("信息：未找到IncludePath节点，创建新节点")
            include_path = ET.SubElement(various_controls, 'IncludePath')
        return include_path
    
    def add_include_path_to_target(self, folder_path, target_node, target_name=None):
        """为特定Target添加Include路径"""
        include_path_node = self.find_include_path_node_for_target(target_node)
        if include_path_node is None:
            print(f"警告：未找到Target '{target_name or 'unknown'}' 的Include路径节点，无法添加路径 {folder_path}")
            return False
            
        # 获取相对路径
        rel_path = self.get_relative_path(folder_path)
        
        # 添加到现有Include路径
        current_paths = []
        if include_path_node.text:
            # 分割路径并去除空白
            current_paths = [p.strip() for p in include_path_node.text.split(';') if p.strip()]
        
        # 检查路径是否已存在（忽略大小写和路径分隔符差异）
        normalized_rel_path = rel_path.lower().replace('\\', '/').rstrip('/')
        normalized_current_paths = [p.lower().replace('\\', '/').rstrip('/') for p in current_paths]
        
        if normalized_rel_path not in normalized_current_paths:
            current_paths.append(rel_path)
            include_path_node.text = ';'.join(current_paths)
            if args.verbose:
                target_info = f" (Target: {target_name})" if target_name else ""
                print(f"添加Include路径{target_info}: {rel_path}")
            return True
        return False
    
    def remove_include_path_from_target(self, folder_path, target_node, target_name=None):
        """从特定Target移除Include路径"""
        include_path_node = self.find_include_path_node_for_target(target_node)
        if include_path_node is None or not include_path_node.text:
            return False
            
        # 获取相对路径
        rel_path = self.get_relative_path(folder_path)
        
        # 从现有Include路径中移除
        current_paths = [p.strip() for p in include_path_node.text.split(';') if p.strip()]
        if not current_paths:
            return False
            
        # 标准化路径进行比较
        normalized_rel_path = rel_path.lower().replace('\\', '/').rstrip('/')
        normalized_current_paths = [(p, p.lower().replace('\\', '/').rstrip('/')) for p in current_paths]
        
        # 查找匹配的路径 - 删除精确匹配和子目录
        removed = False
        new_paths = []
        for orig_path, norm_path in normalized_current_paths:
            # 检查是否为目标路径或其子路径
            if norm_path == normalized_rel_path or norm_path.startswith(normalized_rel_path + '/'):
                removed = True
                if args.verbose:
                    target_info = f" (Target: {target_name})" if target_name else ""
                    print(f"移除Include路径{target_info}: {orig_path}")
            else:
                new_paths.append(orig_path)
        
        if removed:
            include_path_node.text = ';'.join(new_paths) if new_paths else ""
        
        return removed
        
    def add_include_path(self, folder_path):
        """添加Include路径到所有Target"""
        targets = self.find_all_targets()
        
        if not targets:
            print("警告：未找到任何Target，尝试使用旧方法添加Include路径")
            # 向后兼容的方法
            include_path_node = self.find_include_path_node()
            if include_path_node is None:
                print(f"警告：未找到Include路径节点，无法添加路径 {folder_path}")
                return
                
            # 获取相对路径
            rel_path = self.get_relative_path(folder_path)
            
            # 添加到现有Include路径
            current_paths = []
            if include_path_node.text:
                # 分割路径并去除空白
                current_paths = [p.strip() for p in include_path_node.text.split(';') if p.strip()]
            
            # 检查路径是否已存在（忽略大小写和路径分隔符差异）
            normalized_rel_path = rel_path.lower().replace('\\', '/').rstrip('/')
            normalized_current_paths = [p.lower().replace('\\', '/').rstrip('/') for p in current_paths]
            
            if normalized_rel_path not in normalized_current_paths:
                current_paths.append(rel_path)
                include_path_node.text = ';'.join(current_paths)
                if args.verbose:
                    print(f"添加Include路径: {rel_path}")
            return
        
        # 为每个Target添加Include路径
        added = False
        for target_node, target_name in targets:
            if self.add_include_path_to_target(folder_path, target_node, target_name):
                added = True
        
        if not added and args.verbose:
            print(f"信息：路径 {folder_path} 已存在于所有Target的Include路径中")
    
    def remove_include_path(self, folder_path):
        """从所有Target移除Include路径"""
        targets = self.find_all_targets()
        
        if not targets:
            print("警告：未找到任何Target，尝试使用旧方法移除Include路径")
            # 向后兼容的方法
            include_path_node = self.find_include_path_node()
            if include_path_node is None or not include_path_node.text:
                return
                
            # 获取相对路径
            rel_path = self.get_relative_path(folder_path)
            
            # 从现有Include路径中移除
            current_paths = [p.strip() for p in include_path_node.text.split(';') if p.strip()]
            if not current_paths:
                return
                
            # 标准化路径进行比较
            normalized_rel_path = rel_path.lower().replace('\\', '/').rstrip('/')
            normalized_current_paths = [(p, p.lower().replace('\\', '/').rstrip('/')) for p in current_paths]
            
            # 查找匹配的路径
            removed = False
            new_paths = []
            for orig_path, norm_path in normalized_current_paths:
                if norm_path == normalized_rel_path:
                    removed = True
                    if args.verbose:
                        print(f"移除Include路径: {orig_path}")
                else:
                    new_paths.append(orig_path)
            
            if removed:
                include_path_node.text = ';'.join(new_paths) if new_paths else ""
            return
        
        # 从每个Target移除Include路径
        removed = False
        for target_node, target_name in targets:
            if self.remove_include_path_from_target(folder_path, target_node, target_name):
                removed = True
        
        if not removed and args.verbose:
            print(f"信息：未在任何Target中找到路径 {folder_path}")
    
    def add_file(self, file_path, group):
        """添加文件到分组"""
        # 检查文件是否存在
        if not os.path.exists(file_path):
            print(f"警告：文件 {file_path} 不存在，跳过添加")
            return
            
        files = group.find('Files')
        if files is None:
            files = ET.SubElement(group, 'Files')
            
        # 使用相对路径
        rel_path = self.get_relative_path(file_path)
        
        # 检查文件是否已存在于组中
        for file_elem in files.findall('File'):
            file_path_elem = file_elem.find('FilePath')
            if file_path_elem is not None and file_path_elem.text == rel_path:
                print(f"信息：文件 {os.path.basename(file_path)} 已存在于组中，跳过添加")
                return
        
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
        elif ext in ['.s', '.asm']:
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
        
    def scan_and_add_files_to_single_group(self, folder_path, group_name=None):
        """扫描文件夹并将所有文件添加到单一分组中"""
        folder_path = Path(folder_path)
        groups_node = self.root.find('.//Groups')
        if groups_node is None:
            print("错误：未找到Groups节点")
            return
            
        # 添加基础Include路径
        self.add_include_path(str(folder_path))
        
        # 如果未提供组名，则使用文件夹名称
        if group_name is None:
            group_name = folder_path.name
            
        # 创建或查找组
        group = None
        for g in groups_node.findall('Group'):
            name_elem = g.find('GroupName')
            if name_elem is not None and name_elem.text == group_name:
                group = g
                break
                
        if group is None:
            group = ET.SubElement(groups_node, 'Group')
            group_name_elem = ET.SubElement(group, 'GroupName')
            group_name_elem.text = group_name
            
        # 递归遍历文件夹
        for root, dirs, files in os.walk(folder_path):
            # 添加Include路径 - 只添加包含头文件的目录
            has_header = any(f.endswith(('.h', '.hpp')) for f in files)
            if has_header:
                self.add_include_path(root)
            
            # 筛选符合条件的文件
            source_files = [f for f in files if f.endswith(('.c', '.cpp', '.h', '.hpp', '.s', '.asm'))]
            
            # 添加文件到同一个组
            for src_file in source_files:
                file_path = os.path.join(root, src_file)
                self.add_file(file_path, group)
    
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
                
    def remove_file(self, file_path):
        """从项目中移除文件"""
        rel_path = self.get_relative_path(file_path)
        removed = False
        
        # 在所有组中查找文件
        for group in self.root.findall('.//Group'):
            files = group.find('Files')
            if files is None:
                continue
                
            # 查找匹配的文件
            to_remove = []
            for file_elem in files.findall('File'):
                file_path_elem = file_elem.find('FilePath')
                if file_path_elem is not None:
                    file_path_text = file_path_elem.text
                    # 标准化路径进行比较
                    if file_path_text.lower().replace('\\', '/') == rel_path.lower().replace('\\', '/'):
                        to_remove.append(file_elem)
            
            # 移除找到的文件
            for file_elem in to_remove:
                file_name = file_elem.find('FileName')
                file_name_text = file_name.text if file_name is not None else os.path.basename(rel_path)
                files.remove(file_elem)
                removed = True
                if args.verbose:
                    group_name = group.find('GroupName')
                    group_name_text = group_name.text if group_name is not None else "未知组"
                    print(f"从组 '{group_name_text}' 移除文件: {file_name_text}")
        
        return removed
    
    def remove_files_in_folder(self, folder_path):
        """移除文件夹中的所有文件"""
        folder_path = Path(folder_path)
        removed_files = 0
        
        # 递归遍历文件夹
        for root, _, files in os.walk(folder_path):
            # 筛选符合条件的文件
            source_files = [f for f in files if f.endswith(('.c', '.cpp', '.h', '.hpp', '.s', '.asm'))]
            
            # 移除每个文件
            for src_file in source_files:
                file_path = os.path.join(root, src_file)
                if self.remove_file(file_path):
                    removed_files += 1
        
        return removed_files
    
    def print_all_include_paths(self):
        """打印所有Include路径"""
        targets = self.find_all_targets()
        
        if not targets:
            include_node = self.find_include_path_node()
            if include_node is not None and include_node.text:
                print("\n所有Include路径:")
                paths = [p.strip() for p in include_node.text.split(';') if p.strip()]
                for path in paths:
                    print(f"  - {path}")
                return len(paths)
            return 0
        
        total_paths = 0
        for target_node, target_name in targets:
            include_node = self.find_include_path_node_for_target(target_node)
            if include_node is not None and include_node.text:
                paths = [p.strip() for p in include_node.text.split(';') if p.strip()]
                if paths:
                    print(f"\nTarget '{target_name}' 的Include路径:")
                    for path in paths:
                        print(f"  - {path}")
                    total_paths += len(paths)
        
        return total_paths
    
    def print_all_groups_and_files(self):
        """打印所有组和文件"""
        groups_node = self.root.find('.//Groups')
        if groups_node is None:
            print("未找到任何组")
            return 0
            
        total_files = 0
        for group in groups_node.findall('Group'):
            group_name = group.find('GroupName')
            group_name_text = group_name.text if group_name is not None else "未知组"
            
            files = group.find('Files')
            if files is None:
                print(f"\n组 '{group_name_text}': 无文件")
                continue
                
            file_elems = files.findall('File')
            if not file_elems:
                print(f"\n组 '{group_name_text}': 无文件")
                continue
                
            print(f"\n组 '{group_name_text}' ({len(file_elems)}个文件):")
            for file_elem in file_elems:
                file_name = file_elem.find('FileName')
                file_path = file_elem.find('FilePath')
                file_name_text = file_name.text if file_name is not None else "未知文件"
                file_path_text = file_path.text if file_path is not None else ""
                print(f"  - {file_name_text} ({file_path_text})")
                total_files += 1
        
        return total_files
    
    def save(self):
        """保存工程文件"""
        self.tree.write(self.project_file, encoding='utf-8', xml_declaration=True)

    def remove_group_by_name(self, group_name):
        """根据组名移除组"""
        groups_node = self.root.find('.//Groups')
        if groups_node is None:
            return False
            
        removed = False
        for group in groups_node.findall('Group'):
            name_elem = group.find('GroupName')
            if name_elem is not None and name_elem.text == group_name:
                groups_node.remove(group)
                removed = True
                if args.verbose:
                    print(f"移除组: '{group_name}'")
                break
        
        return removed
    
    def find_group_by_folder_name(self, folder_path):
        """根据文件夹名查找组"""
        folder_name = os.path.basename(folder_path)
        groups_node = self.root.find('.//Groups')
        if groups_node is None:
            return None
            
        for group in groups_node.findall('Group'):
            name_elem = group.find('GroupName')
            if name_elem is not None and name_elem.text == folder_name:
                return name_elem.text
        
        return None

def main():
    # 解析命令行参数
    parser = argparse.ArgumentParser(description='Keil项目文件助手 - 添加/删除文件到Keil项目')
    parser.add_argument('-p', '--project', required=True, help='Keil项目文件路径(.uvprojx)')
    parser.add_argument('-f', '--folder', help='要处理的文件夹路径')
    parser.add_argument('-g', '--group', help='指定添加到的组名称(不指定则使用文件夹名)')
    parser.add_argument('-r', '--recursive', action='store_true', help='递归创建文件夹结构(默认为添加到单一组)')
    parser.add_argument('-v', '--verbose', action='store_true', help='显示详细信息')
    parser.add_argument('-d', '--delete', action='store_true', help='删除模式(删除指定文件夹中的文件和Include路径)')
    parser.add_argument('-l', '--list', action='store_true', help='列出项目中的所有Target、Include路径和文件')
    parser.add_argument('--delete-group', help='删除指定名称的组')
    
    global args
    args = parser.parse_args()
    
    # 检查项目文件是否存在
    if not os.path.exists(args.project):
        print(f"错误：项目文件 {args.project} 不存在")
        sys.exit(1)
    
    # 转换项目文件为绝对路径
    project_path = os.path.abspath(args.project)
    
    try:
        manager = KeilProjectManager(project_path)
        
        # 列出模式
        if args.list:
            print(f"项目文件: {project_path}")
            targets = manager.find_all_targets()
            if targets:
                print(f"\n项目中的Target ({len(targets)}):")
                for _, target_name in targets:
                    print(f"  - {target_name}")
            
            include_count = manager.print_all_include_paths()
            file_count = manager.print_all_groups_and_files()
            
            print(f"\n总计: {len(targets) if targets else 0}个Target, {include_count}个Include路径, {file_count}个文件")
            return
        
        # 检查文件夹参数
        if not args.folder:
            print("错误：需要指定文件夹路径")
            sys.exit(1)
            
        if not os.path.exists(args.folder):
            print(f"错误：文件夹 {args.folder} 不存在")
            sys.exit(1)
        
        # 转换为绝对路径
        folder_path = os.path.abspath(args.folder)
        
        if args.verbose:
            print(f"项目文件: {project_path}")
            print(f"处理文件夹: {folder_path}")
            if args.group:
                print(f"组名称: {args.group}")
            print(f"模式: {'删除' if args.delete else '添加'}")
            print(f"递归模式: {'是' if args.recursive else '否'}")
            
            # 显示项目中的所有Target
            targets = manager.find_all_targets()
            if targets:
                print(f"\n项目中的Target ({len(targets)}):")
                for _, target_name in targets:
                    print(f"  - {target_name}")
        
        if args.delete_group:
            # 删除指定组
            if manager.remove_group_by_name(args.delete_group):
                manager.save()
                print(f"已成功从项目 {args.project} 中删除组 '{args.delete_group}'")
            else:
                print(f"错误：未找到组 '{args.delete_group}'")
            return
            
        if args.delete:
            # 删除模式
            removed_files = manager.remove_files_in_folder(folder_path)
            manager.remove_include_path(folder_path)
            
            # 如果指定了组名，删除该组
            group_deleted = False
            if args.group:
                group_deleted = manager.remove_group_by_name(args.group)
            else:
                # 尝试查找与文件夹名相同的组并删除
                folder_name = os.path.basename(folder_path)
                group_deleted = manager.remove_group_by_name(folder_name)
            
            manager.save()
            
            group_info = ""
            if args.group and group_deleted:
                group_info = f", 已删除组 '{args.group}'"
            elif group_deleted:
                group_info = f", 已删除组 '{os.path.basename(folder_path)}'"
                
            print(f"已成功从项目 {args.project} 中删除 {args.folder} 相关的文件和路径{group_info} (移除了{removed_files}个文件)")
        else:
            # 添加模式
            if args.recursive:
                # 使用原始方法，递归创建文件夹结构
                manager.scan_and_add_files(folder_path)
            else:
                # 使用新方法，将所有文件添加到单一组
                manager.scan_and_add_files_to_single_group(folder_path, args.group)
                
            manager.save()
            print(f"已成功将 {args.folder} 中的文件添加到项目 {args.project}")
        
        # 显示添加的Include路径
        if args.verbose:
            targets = manager.find_all_targets()
            if not targets:
                include_node = manager.find_include_path_node()
                if include_node is not None and include_node.text:
                    print("\n当前Include路径:")
                    for path in include_node.text.split(';'):
                        if path.strip():
                            print(f"  - {path}")
            else:
                for target_node, target_name in targets:
                    include_node = manager.find_include_path_node_for_target(target_node)
                    if include_node is not None and include_node.text:
                        print(f"\nTarget '{target_name}' 的Include路径:")
                        for path in include_node.text.split(';'):
                            if path.strip():
                                print(f"  - {path}")
    except Exception as e:
        print(f"错误：处理过程中发生异常：{str(e)}")
        import traceback
        traceback.print_exc()
        sys.exit(1)

if __name__ == "__main__":
    main()