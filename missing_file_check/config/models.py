"""配置数据模型"""

from enum import Enum
from typing import Dict, List, Optional, Any
from pydantic import BaseModel, Field


class ProjectType(str, Enum):
    """工程类型枚举"""
    API = "api"  # 通过API接口获取（公司检查平台）
    FTP = "ftp"  # 通过FTP获取离线日志
    FILE = "file"  # 本地文件系统
    PLATFORM_A = "platform_a"  # 检查平台A
    PLATFORM_B = "platform_b"  # 检查平台B
    CUSTOM = "custom"  # 自定义类型


class ProjectConfig(BaseModel):
    """工程配置"""
    project_id: str = Field(..., description="工程ID")
    project_name: str = Field(..., description="工程名称")
    project_type: ProjectType = Field(..., description="工程类型")
    connection_config: Dict[str, Any] = Field(
        default_factory=dict, 
        description="连接配置（根据类型不同而不同）"
    )
    metadata: Optional[Dict[str, Any]] = Field(
        default=None, 
        description="其他元数据"
    )


class ShieldConfig(BaseModel):
    """屏蔽配置"""
    id: str = Field(..., description="配置ID")
    pattern: str = Field(..., description="路径模式（支持正则/通配符）")
    remark: str = Field(default="", description="备注信息")
    enabled: bool = Field(default=True, description="是否启用")


class PathMappingConfig(BaseModel):
    """路径映射配置"""
    id: str = Field(..., description="配置ID")
    source_pattern: str = Field(..., description="源路径模式")
    target_pattern: str = Field(..., description="目标路径模式")
    remark: str = Field(default="", description="备注信息")
    enabled: bool = Field(default=True, description="是否启用")


class PathPrefixConfig(BaseModel):
    """路径前缀配置"""
    project_id: str = Field(..., description="工程ID")
    prefix: str = Field(..., description="路径前缀")
    trim_prefix: bool = Field(default=True, description="是否移除前缀")


class ComponentInfo(BaseModel):
    """组件信息"""
    component_id: str = Field(..., description="组件ID")
    component_name: str = Field(..., description="组件名称")


class ProjectMapping(BaseModel):
    """工程映射关系"""
    target_projects: List[str] = Field(
        default_factory=list, 
        description="待检查工程ID列表"
    )
    baseline_projects: List[str] = Field(
        default_factory=list, 
        description="基线工程ID列表"
    )


class TaskConfig(BaseModel):
    """任务配置"""
    task_id: str = Field(..., description="任务ID")
    components: List[ComponentInfo] = Field(
        default_factory=list, 
        description="关联的组件信息"
    )
    project_mappings: List[ProjectMapping] = Field(
        default_factory=list, 
        description="工程映射关系"
    )
    shield_configs: List[ShieldConfig] = Field(
        default_factory=list, 
        description="屏蔽配置列表"
    )
    path_mappings: List[PathMappingConfig] = Field(
        default_factory=list, 
        description="路径映射配置列表"
    )
    path_prefixes: List[PathPrefixConfig] = Field(
        default_factory=list, 
        description="路径前缀配置列表"
    )
    project_configs: Dict[str, ProjectConfig] = Field(
        default_factory=dict,
        description="工程配置字典，key为project_id"
    )
