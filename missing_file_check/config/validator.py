"""配置验证器"""

from missing_file_check.config.models import TaskConfig


class ConfigValidator:
    """配置验证器 - 确保配置数据完整性"""
    
    @staticmethod
    def validate(config: TaskConfig) -> bool:
        """
        验证任务配置
        
        Args:
            config: 任务配置对象
            
        Returns:
            bool: 配置是否有效
            
        Raises:
            ValueError: 配置验证失败，附带详细错误信息
        """
        # 验证工程映射关系
        for mapping in config.project_mappings:
            if not mapping.target_projects:
                raise ValueError("Project mapping must have at least one target project")
            if not mapping.baseline_projects:
                raise ValueError("Project mapping must have at least one baseline project")
            
            # 验证所有引用的工程都有配置
            all_project_ids = set(mapping.target_projects + mapping.baseline_projects)
            for project_id in all_project_ids:
                if project_id not in config.project_configs:
                    raise ValueError(f"Project {project_id} referenced but not configured")
        
        # TODO: 添加更多验证逻辑
        # - 屏蔽配置的pattern格式验证
        # - 路径映射配置的pattern验证
        # - 路径前缀配置验证
        
        return True
