import logging
import requests
import time
import json
from datetime import datetime

from app.config.settings import CONFIG
from app.services.notifier import notifier

logger = logging.getLogger(__name__)

class ServiceChecker:
    """鏈嶅姟妫€鏌ュ櫒锛屽畾鏃舵鏌ユ寚瀹氱殑鏈嶅姟绔偣鐘舵€?""
    
    def __init__(self):
        self.config = CONFIG["service_checks"]
        self.endpoints = self.config.get("endpoints", [])
        self.timeout = 10  # 璇锋眰瓒呮椂鏃堕棿锛堢锛?        self.status_history = {}  # 瀛樺偍鏈嶅姟鐘舵€佸巻鍙?        self.default_interval = self.config.get("interval_minutes", 5)  # 榛樿妫€鏌ラ棿闅旓紙鍒嗛挓锛?    
    def add_endpoint(self, name, url, expected_status=200, expected_content=None, headers=None, 
                     method="GET", body=None, interval_minutes=None, json_check=None):
        """
        娣诲姞鏈嶅姟妫€鏌ョ鐐?        
        Args:
            name: 鏈嶅姟鍚嶇О
            url: 鏈嶅姟URL
            expected_status: 棰勬湡HTTP鐘舵€佺爜
            expected_content: 棰勬湡杩斿洖鍐呭锛堝瓧绗︿覆鎴朜one锛?            headers: 璇锋眰澶达紙瀛楀吀鎴朜one锛?            method: 璇锋眰鏂规硶锛圙ET鎴朠OST锛?            body: 璇锋眰浣擄紙鐢ㄤ簬POST璇锋眰锛?            interval_minutes: 妫€鏌ラ棿闅旀椂闂达紙鍒嗛挓锛?            json_check: JSON鍝嶅簲妫€鏌ラ厤缃紝鏍煎紡涓?{"path": "key1.key2[0].key3", "expected_value": "value"}
        """
        # 妫€鏌ユ槸鍚﹀凡瀛樺湪鍚屽悕绔偣
        for existing_endpoint in self.endpoints:
            if existing_endpoint["name"] == name:
                logger.info(f"绔偣宸插瓨鍦紝璺宠繃娣诲姞: {name}")
                return
                
        endpoint = {
            "name": name,
            "url": url,
            "expected_status": expected_status,
            "expected_content": expected_content,
            "headers": headers or {},
            "method": method.upper(),
            "body": body,
            "interval_minutes": interval_minutes or self.default_interval,
            "json_check": json_check
        }
        self.endpoints.append(endpoint)
        logger.info(f"娣诲姞鏈嶅姟妫€鏌ョ鐐? {name} - {url} ({method}), 妫€鏌ラ棿闅? {endpoint['interval_minutes']}鍒嗛挓")
    
    def get_endpoint_interval(self, endpoint):
        """
        鑾峰彇绔偣鐨勬鏌ラ棿闅旀椂闂?        
        Args:
            endpoint: 绔偣閰嶇疆鎴栫鐐瑰悕绉?            
        Returns:
            int: 妫€鏌ラ棿闅旀椂闂达紙鍒嗛挓锛?        """
        if isinstance(endpoint, dict):
            return endpoint.get("interval_minutes", self.default_interval)
        elif isinstance(endpoint, str):
            # 閫氳繃鍚嶇О鏌ユ壘绔偣
            for ep in self.endpoints:
                if ep["name"] == endpoint:
                    return ep.get("interval_minutes", self.default_interval)
        return self.default_interval
    
    def _check_json_path(self, json_data, path, expected_value):
        """
        妫€鏌SON鏁版嵁涓寚瀹氳矾寰勭殑鍊兼槸鍚﹀尮閰嶉鏈?        
        Args:
            json_data: JSON鏁版嵁锛堝瓧鍏革級
            path: 鏁版嵁璺緞锛屾牸寮忓 "result.stats[0].blockchain"
            expected_value: 棰勬湡鍊?            
        Returns:
            bool: 鏄惁鍖归厤
        """
        try:
            # 瑙ｆ瀽璺緞
            parts = path.split('.')
            current = json_data
            
            for part in parts:
                # 澶勭悊鏁扮粍绱㈠紩锛屽 stats[0]
                if '[' in part and ']' in part:
                    key, idx_str = part.split('[', 1)
                    idx = int(idx_str.split(']')[0])
                    current = current.get(key, [])[idx]
                else:
                    current = current.get(part)
                
                # 濡傛灉璺緞涓€旀柇浜嗭紝杩斿洖False
                if current is None:
                    logger.debug(f"JSON璺緞 {path} 涓殑閮ㄥ垎 {part} 涓嶅瓨鍦?)
                    return False
            
            # 姣旇緝鏈€缁堝€?            result = str(current) == str(expected_value)
            logger.debug(f"JSON妫€鏌? 璺緞={path}, 瀹為檯鍊?{current}, 棰勬湡鍊?{expected_value}, 缁撴灉={result}")
            return result
            
        except (KeyError, IndexError, AttributeError, TypeError) as e:
            logger.warning(f"JSON妫€鏌ュけ璐? {str(e)}")
            return False
    
    def check_service(self, endpoint):
        """
        妫€鏌ュ崟涓湇鍔＄姸鎬?        
        Args:
            endpoint: 鏈嶅姟绔偣閰嶇疆
            
        Returns:
            (bool, str): (鏄惁姝ｅ父, 璇︾粏淇℃伅)
        """
        name = endpoint["name"]
        url = endpoint["url"]
        method = endpoint.get("method", "GET").upper()
        expected_status = endpoint.get("expected_status", 200)
        expected_content = endpoint.get("expected_content")
        headers = endpoint.get("headers", {})
        body = endpoint.get("body")
        json_check = endpoint.get("json_check")
        
        start_time = time.time()
        try:
            if method == "GET":
                response = requests.get(url, headers=headers, timeout=self.timeout)
            elif method == "POST":
                response = requests.post(url, headers=headers, json=body if isinstance(body, dict) else None, 
                                         data=body if not isinstance(body, dict) else None, timeout=self.timeout)
            else:
                return False, f"涓嶆敮鎸佺殑璇锋眰鏂规硶: {method}"
                
            response_time = time.time() - start_time
            
            # 妫€鏌ョ姸鎬佺爜
            status_ok = response.status_code == expected_status
            
            # 妫€鏌ヨ繑鍥炲唴瀹癸紙瀛楃涓插尮閰嶏級
            content_ok = True
            if expected_content and expected_content not in response.text:
                content_ok = False
            
            # 妫€鏌SON缁撴瀯锛堝鏋滈厤缃簡锛?            json_ok = True
            if json_check and status_ok:
                try:
                    json_data = response.json()
                    json_ok = self._check_json_path(
                        json_data, 
                        json_check["path"], 
                        json_check["expected_value"]
                    )
                except json.JSONDecodeError:
                    logger.warning(f"鏈嶅姟 {name} 杩斿洖鐨勪笉鏄湁鏁堢殑JSON鏁版嵁")
                    json_ok = False
            
            # 鏈€缁堟鏌ョ粨鏋?            check_ok = status_ok and content_ok and json_ok
            
            if check_ok:
                return True, f"鏈嶅姟姝ｅ父 ({response.status_code}, {response_time:.2f}s)"
            else:
                fail_reason = []
                if not status_ok:
                    fail_reason.append(f"鐘舵€佺爜 {response.status_code} (棰勬湡 {expected_status})")
                if not content_ok:
                    fail_reason.append("杩斿洖鍐呭涓嶇鍚堥鏈?)
                if not json_ok and json_check:
                    fail_reason.append(f"JSON瀛楁妫€鏌ュけ璐? {json_check['path']}")
                
                return False, f"鏈嶅姟寮傚父: {', '.join(fail_reason)}"
                
        except requests.RequestException as e:
            return False, f"鏈嶅姟璇锋眰寮傚父: {str(e)}"
    
    def check_endpoint_by_name(self, name):
        """
        閫氳繃鍚嶇О妫€鏌ユ寚瀹氱殑绔偣
        
        Args:
            name: 绔偣鍚嶇О
            
        Returns:
            (bool, str): (鏄惁姝ｅ父, 璇︾粏淇℃伅) 鎴?(False, "绔偣涓嶅瓨鍦?)
        """
        for endpoint in self.endpoints:
            if endpoint["name"] == name:
                return self.check_service(endpoint)
        return False, "绔偣涓嶅瓨鍦?
    
    def run_checks(self):
        """杩愯鎵€鏈夋湇鍔℃鏌?""
        if not self.config["enabled"]:
            logger.info("鏈嶅姟妫€鏌ュ姛鑳藉凡绂佺敤")
            return
        
        logger.info("寮€濮嬫湇鍔＄姸鎬佹鏌?..")
        check_time = datetime.now()
        
        for endpoint in self.endpoints:
            name = endpoint["name"]
            url = endpoint["url"]
            method = endpoint.get("method", "GET")
            
            logger.info(f"妫€鏌ユ湇鍔? {name} ({method} {url})")
            is_ok, details = self.check_service(endpoint)
            
            # 璁板綍璇︾粏鏃ュ織
            logger.info(f"鏈嶅姟 {name} 鍘熷妫€鏌ョ粨鏋? is_ok={is_ok}, details={details}")
            
            # 鑾峰彇璇ユ湇鍔＄殑鍘嗗彶鐘舵€?            previous_status = self.status_history.get(name, {}).get("is_ok")
            # 璁板綍鍘嗗彶鐘舵€?            logger.info(f"鏈嶅姟 {name} 鍘嗗彶鐘舵€? previous_status={previous_status}")
            
            # 淇濆瓨褰撳墠鍘嗗彶鐘舵€佺敤浜庡垽鏂彉鍖?            status_changed = False
            if previous_status is not None and previous_status != is_ok:
                status_changed = True
                change_type = "鎭㈠姝ｅ父" if is_ok else "鍙樹负寮傚父"
                logger.info(f"妫€娴嬪埌鏈嶅姟 {name} 鐘舵€佸彉鍖? {change_type}")
            
            # 鏈嶅姟鐘舵€佸彉鍖栨椂鍙戦€侀€氱煡锛堜笉绠℃槸浠€涔堝彉鍖栵級
            if status_changed:
                if is_ok:
                    # 鏈嶅姟浠庡紓甯告仮澶嶄负姝ｅ父
                    logger.info(f"鏈嶅姟 {name} 浠庡紓甯告仮澶嶄负姝ｅ父锛屽噯澶囧彂閫佹仮澶嶉€氱煡")
                    message = f"鉁?鏈嶅姟 {name} ({method} {url}) 宸叉仮澶嶆甯竆n璇︽儏: {details}"
                    level = "warning"  # 浣跨敤warning绾у埆纭繚閫氱煡鏄庢樉
                else:
                    # 鏈嶅姟浠庢甯稿彉涓哄紓甯?                    logger.info(f"鏈嶅姟 {name} 浠庢甯稿彉涓哄紓甯革紝鍑嗗鍙戦€佸紓甯搁€氱煡")
                    message = f"鉂?鏈嶅姟 {name} ({method} {url}) 鍙樹负寮傚父\n璇︽儏: {details}"
                    level = "error"
                
                logger.info(f"鍙戦€佹湇鍔＄姸鎬佸彉鍖栭€氱煡: 鏈嶅姟={name}, 鍙樺寲={'鎭㈠姝ｅ父' if is_ok else '鍙樹负寮傚父'}, 绾у埆={level}")
                # 灏濊瘯鍙戦€侀€氱煡锛屽苟璁板綍缁撴灉
                notification_sent = notifier.send_notification(f"鏈嶅姟鐘舵€佸彉鍖? {name}", message, level)
                logger.info(f"鏈嶅姟鐘舵€佸彉鍖栭€氱煡鍙戦€佺粨鏋? {'鎴愬姛' if notification_sent else '澶辫触'}")
                
            elif previous_status is None and not is_ok:
                # 棣栨妫€鏌ュ氨鍙戠幇鏈嶅姟寮傚父鏃跺彂閫侀€氱煡
                logger.info(f"棣栨妫€鏌ュ彂鐜版湇鍔?{name} 寮傚父锛屽噯澶囧彂閫侀娆″紓甯搁€氱煡")
                message = f"鉂?鏈嶅姟 {name} ({method} {url}) 寮傚父\n璇︽儏: {details}"
                notification_sent = notifier.send_notification(f"鏈嶅姟寮傚父: {name}", message, "error")
                logger.info(f"棣栨鏈嶅姟寮傚父閫氱煡鍙戦€佺粨鏋? {'鎴愬姛' if notification_sent else '澶辫触'}")
            
            # 鏇存柊鐘舵€佸巻鍙诧紙鏀惧湪閫氱煡鍙戦€佷箣鍚庯紝浠ョ‘淇濇纭崟鑾风姸鎬佸彉鍖栵級
            self.status_history[name] = {
                "is_ok": is_ok,
                "details": details,
                "last_check": check_time
            }
            
            logger.info(f"鏈嶅姟 {name} 妫€鏌ョ粨鏋? {'姝ｅ父' if is_ok else '寮傚父'} - {details}")
        
        logger.info("鏈嶅姟鐘舵€佹鏌ュ畬鎴?)
    
    def get_status_summary(self):
        """鑾峰彇鎵€鏈夋湇鍔＄殑鐘舵€佹憳瑕?""
        if not self.status_history:
            return "鏃犳湇鍔℃鏌ヨ褰?
        
        summary = []
        for name, status in self.status_history.items():
            state = "姝ｅ父" if status["is_ok"] else "寮傚父"
            last_check = status["last_check"].strftime("%Y-%m-%d %H:%M:%S")
            summary.append(f"{name}: {state} (涓婃妫€鏌? {last_check})")
        
        return "\n".join(summary)
        
    def send_test_notification(self):
        """鍙戦€佹祴璇曢€氱煡锛岀敤浜庨獙璇侀€氱煡鍔熻兘鏄惁姝ｅ父宸ヤ綔"""
        logger.info("鍙戦€佹祴璇曢€氱煡...")
        
        # 鍙戦€佹祴璇曢偖浠堕€氱煡
        email_message = "杩欐槸涓€鏉℃祴璇曢偖浠堕€氱煡锛岀敤浜庨獙璇侀偖浠堕€氱煡鍔熻兘鏄惁姝ｅ父宸ヤ綔銆?
        email_result = notifier.send_email("鏈嶅姟鐩戞帶娴嬭瘯閭欢", email_message)
        logger.info(f"娴嬭瘯閭欢鍙戦€佺粨鏋? {'鎴愬姛' if email_result else '澶辫触'}")
        
        # 鍙戦€佹祴璇昑elegram閫氱煡
        telegram_message = "杩欐槸涓€鏉℃祴璇昑elegram閫氱煡锛岀敤浜庨獙璇乀elegram閫氱煡鍔熻兘鏄惁姝ｅ父宸ヤ綔銆?
        telegram_result = notifier.send_telegram("鏈嶅姟鐩戞帶娴嬭瘯Telegram", telegram_message)
        logger.info(f"娴嬭瘯Telegram鍙戦€佺粨鏋? {'鎴愬姛' if telegram_result else '澶辫触'}")
        
        # 浣跨敤閫氱煡鏈嶅姟鍙戦€佺患鍚堟祴璇?        test_message = "杩欐槸涓€鏉＄患鍚堟祴璇曢€氱煡锛屽悓鏃舵祴璇曢偖浠跺拰Telegram閫氱煡鍔熻兘銆俓n\n濡傛灉鎮ㄦ敹鍒版娑堟伅锛岃〃绀洪€氱煡绯荤粺宸ヤ綔姝ｅ父銆?
        notification_result = notifier.send_notification("鏈嶅姟鐩戞帶绯荤粺娴嬭瘯", test_message, "warning")
        logger.info(f"缁煎悎娴嬭瘯閫氱煡鍙戦€佺粨鏋? {'鎴愬姛' if notification_result else '澶辫触'}")
        
        return {
            "email": email_result,
            "telegram": telegram_result,
            "notification": notification_result
        }

# 鍒涘缓鏈嶅姟妫€鏌ュ疄渚?service_checker = ServiceChecker() 
