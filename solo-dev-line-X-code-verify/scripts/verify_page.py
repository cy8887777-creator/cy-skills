#!/usr/bin/env python3
"""
页面验证脚本
用于检查页面是否可访问、响应是否正常、HTML结构是否完整

使用方法：
    python verify_page.py --url <页面地址>

参数：
    --url: 目标页面的完整URL（必需）

输出：
    JSON格式的验证报告
"""

import argparse
import json
import sys
import time
from typing import Dict, List, Any

try:
    import requests
except ImportError:
    print(json.dumps({
        "accessible": False,
        "error": "缺少依赖：requests库未安装，请执行 pip install requests",
        "issues": ["依赖缺失：requests"]
    }))
    sys.exit(1)


def check_page_accessibility(url: str, timeout: int = 10) -> Dict[str, Any]:
    """
    检查页面可访问性和基础结构
    
    Args:
        url: 目标页面URL
        timeout: 请求超时时间（秒）
    
    Returns:
        验证报告字典
    """
    result = {
        "url": url,
        "accessible": False,
        "status_code": None,
        "response_time": None,
        "has_html_structure": False,
        "issues": [],
        "details": {}
    }
    
    try:
        # 发送HTTP请求
        start_time = time.time()
        response = requests.get(url, timeout=timeout)
        end_time = time.time()
        
        result["status_code"] = response.status_code
        result["response_time"] = round((end_time - start_time) * 1000, 2)  # 毫秒
        result["details"]["content_length"] = len(response.content)
        
        # 检查HTTP状态码
        if response.status_code == 200:
            result["accessible"] = True
        else:
            result["issues"].append(f"HTTP状态码异常：{response.status_code}")
            return result
        
        # 检查HTML基础结构
        content = response.text.lower()
        
        has_doctype = "<!doctype" in content or "<!doctype html>" in content
        has_html_tag = "<html" in content
        has_head = "<head" in content
        has_body = "<body" in content
        
        result["details"]["structure"] = {
            "has_doctype": has_doctype,
            "has_html_tag": has_html_tag,
            "has_head": has_head,
            "has_body": has_body
        }
        
        if has_html_tag and has_body:
            result["has_html_structure"] = True
        else:
            result["issues"].append("HTML结构不完整：缺少必要的HTML标签")
        
        # 检查是否包含React/Vue等框架挂载点
        if "<div id=" in content or "id=\"root\"" in content or "id=\"app\"" in content:
            result["details"]["has_mount_point"] = True
        else:
            result["details"]["has_mount_point"] = False
            result["issues"].append("未检测到框架挂载点（如 <div id='root'>）")
        
        # 检查是否包含script标签（JS应用）
        if "<script" in content:
            result["details"]["has_scripts"] = True
        else:
            result["details"]["has_scripts"] = False
            result["issues"].append("页面未包含JavaScript脚本")
        
    except requests.exceptions.Timeout:
        result["issues"].append(f"请求超时：超过{timeout}秒未响应")
    except requests.exceptions.ConnectionError:
        result["issues"].append("连接失败：无法访问目标地址，请检查服务器是否启动")
    except requests.exceptions.RequestException as e:
        result["issues"].append(f"请求异常：{str(e)}")
    except Exception as e:
        result["issues"].append(f"未知错误：{str(e)}")
    
    return result


def main():
    parser = argparse.ArgumentParser(
        description="验证页面可访问性和基础结构",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
示例：
    python verify_page.py --url http://localhost:3000
    python verify_page.py --url http://localhost:5173
        """
    )
    
    parser.add_argument(
        "--url",
        required=True,
        help="目标页面的完整URL"
    )
    
    parser.add_argument(
        "--timeout",
        type=int,
        default=10,
        help="请求超时时间（秒），默认10秒"
    )
    
    args = parser.parse_args()
    
    # 执行验证
    report = check_page_accessibility(args.url, args.timeout)
    
    # 输出JSON报告
    print(json.dumps(report, indent=2, ensure_ascii=False))
    
    # 根据验证结果设置退出码
    if report["accessible"] and report["has_html_structure"]:
        sys.exit(0)
    else:
        sys.exit(1)


if __name__ == "__main__":
    main()
