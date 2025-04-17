import sys
import logging
import argparse
from app.services.service_check import service_checker
from app.services.notifier import notifier

logger = logging.getLogger(__name__)

def main():
    """程序入口点"""
    parser = argparse.ArgumentParser(description='EVM服务监控工具')
    
    # 添加子命令
    subparsers = parser.add_subparsers(dest='command', help='选择要执行的命令')
    
    # 测试通知命令
    test_parser = subparsers.add_parser('test_notify', help='测试通知功能')
    
    # 检查服务命令
    check_parser = subparsers.add_parser('check', help='检查服务状态')
    
    # 解析命令行参数
    args = parser.parse_args()
    
    # 根据命令执行对应功能
    if args.command == 'test_notify':
        logger.info("执行通知测试")
        results = service_checker.send_test_notification()
        print("通知测试结果:")
        
        # 检查结果字典中是否包含特定键
        if 'email' in results:
            print(f"邮件通知: {'成功' if results['email'] else '失败'}")
        if 'telegram' in results:
            print(f"Telegram通知: {'成功' if results['telegram'] else '失败'}")
        if 'notification' in results:
            print(f"综合通知: {'成功' if results['notification'] else '失败'}")
        
        print("\n检查app.log日志文件以获取更多详细信息")
        
    elif args.command == 'check':
        logger.info("执行服务检查")
        service_checker.run_checks()
        status = service_checker.get_status_summary()
        print("服务状态摘要:")
        print(status)
        
    else:
        parser.print_help()
        
if __name__ == "__main__":
    main() 