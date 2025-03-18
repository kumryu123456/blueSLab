#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""
BlueAI 클라이언트 - 환율 조회 작업
"""

import logging
import re
import os
import csv
from datetime import datetime
from automation.tasks.base_task import BaseTask

logger = logging.getLogger(__name__)

class ExchangeRateTask(BaseTask):
    """실시간 환율 정보를 조회하는 작업"""
    
    def __init__(self, browser_manager):
        super().__init__(browser_manager)
        
        # 작업 관련 키워드
        self.keywords = ["환율", "환전", "외환", "달러", "엔", "유로", "위안", "파운드"]
        
        # 매개변수 설정
        self.required_params = ["currency"]
        self.optional_params = {
            "amount": "1",
            "save_results": "false",
            "save_path": os.path.join(os.path.expanduser("~"), "Documents", "BlueAI")
        }
        
        # 통화 코드 매핑
        self.currency_map = {
            "달러": "USD",
            "엔": "JPY",
            "유로": "EUR",
            "위안": "CNY",
            "파운드": "GBP",
            "호주달러": "AUD",
            "캐나다달러": "CAD",
            "프랑": "CHF",
            "홍콩달러": "HKD",
            "링깃": "MYR",
            "싱가포르달러": "SGD",
            "태국바트": "THB",
            "대만달러": "TWD"
        }
    
    def get_param_pattern(self, param):
        """환율 작업에 특화된 매개변수 추출 패턴"""
        if param == "currency":
            # 통화명 매칭 (달러, 엔, 유로 등)
            currency_names = "|".join(self.currency_map.keys())
            return f'({currency_names}|[A-Z]{{3}})'
        elif param == "amount":
            # 금액 매칭 (숫자+통화명)
            return r'(\d+(?:\.\d+)?(?:\s*(?:만|천|억))?)'
        elif param == "save_results":
            # 저장 여부 매칭
            return r'(저장|보관|기록|save)'
        else:
            # 기본 패턴 사용
            return super().get_param_pattern(param)
    
    def extract_params(self, command):
        """명령어에서 매개변수 추출 - 환율 작업 특화"""
        params = {}
        command_lower = command.lower()
        
        # 통화 추출
        currency = None
        for curr_name in self.currency_map:
            if curr_name in command_lower:
                currency = curr_name
                break
        
        # 직접 ISO 코드로 통화 지정한 경우 (USD, EUR 등)
        if not currency:
            iso_match = re.search(r'\b([A-Z]{3})\b', command)
            if iso_match:
                currency_code = iso_match.group(1)
                # 통화 코드를 역으로 찾기
                for name, code in self.currency_map.items():
                    if code == currency_code:
                        currency = name
                        break
                if not currency:
                    # 매핑에 없는 통화 코드는 그대로 사용
                    currency = currency_code
        
        if currency:
            params["currency"] = currency
        
        # 금액 추출
        amount_match = re.search(r'(\d+(?:\.\d+)?)', command)
        if amount_match:
            try:
                amount = float(amount_match.group(1))
                
                # 단위 변환 (만, 천, 억)
                if "만" in command:
                    amount *= 10000
                elif "천" in command:
                    amount *= 1000
                elif "억" in command:
                    amount *= 100000000
                
                params["amount"] = str(amount)
            except ValueError:
                params["amount"] = "1"
        else:
            params["amount"] = "1"
        
        # 저장 여부
        save_keywords = ["저장", "보관", "기록", "save"]
        save_results = "true" if any(keyword in command_lower for keyword in save_keywords) else "false"
        params["save_results"] = save_results
        
        # 나머지 선택적 매개변수는 기본값에서 가져옴
        for param, default_value in self.optional_params.items():
            if param not in params:
                params[param] = default_value
        
        return params
    
    def execute(self, params):
        """환율 조회 작업 실행"""
        logger.info(f"환율 조회 작업 실행: {params}")
        
        # 매개변수 검증
        if "currency" not in params:
            raise ValueError("통화 종류를 지정해야 합니다.")
        
        currency = params["currency"]
        amount = float(params.get("amount", 1))
        save_results = params.get("save_results") == "true"
        save_path = params.get("save_path")
        
        # ISO 통화 코드 변환
        currency_code = self.currency_map.get(currency, currency)
        
        # 브라우저 초기화
        browser = self.browser_manager.get_browser()
        page = browser.new_page()
        
        try:
            # 환율 정보 사이트 접속
            logger.info("환율 정보 사이트 접속 중...")
            page.goto("https://www.investing.com/currencies/exchange-rates-table")
            page.wait_for_load_state("networkidle")
            
            # 검색창 찾기 및 통화 검색
            page.fill('input.searchText', currency_code)
            page.press('input.searchText', 'Enter')
            page.wait_for_selector('table#cr1', timeout=10000)
            
            # 환율 데이터 추출
            exchange_rates = []
            rows = page.query_selector_all('table#cr1 tbody tr')
            
            for row in rows:
                try:
                    cells = row.query_selector_all('td')
                    if len(cells) < 5:  # 최소 5개 열이 있어야 함
                        continue
                    
                    pair_elem = cells[1].query_selector('a')
                    if not pair_elem:
                        continue
                    
                    pair = pair_elem.inner_text().strip()
                    
                    # 찾고자 하는 통화 코드가 포함된 경우만 처리
                    if currency_code in pair:
                        base_currency, quote_currency = pair.split('/')
                        
                        rate = cells[2].inner_text().strip()
                        try:
                            rate_value = float(rate.replace(',', ''))
                        except ValueError:
                            rate_value = 0.0
                        
                        change = cells[3].inner_text().strip()
                        change_pct = cells[4].inner_text().strip()
                        
                        # 기준 통화가 찾는 통화인 경우 (KRW/USD 등)
                        if base_currency == currency_code:
                            exchange_rates.append({
                                "pair": pair,
                                "base_currency": base_currency,
                                "quote_currency": quote_currency,
                                "rate": rate,
                                "rate_value": rate_value,
                                "change": change,
                                "change_percent": change_pct,
                                "is_direct": True  # 직접 환율
                            })
                        # 호가 통화가 찾는 통화인 경우 (USD/KRW 등)
                        elif quote_currency == currency_code:
                            # 역환율 계산
                            inverse_rate_value = 1.0 / rate_value if rate_value else 0.0
                            
                            exchange_rates.append({
                                "pair": f"{quote_currency}/{base_currency}",
                                "base_currency": quote_currency,
                                "quote_currency": base_currency,
                                "rate": f"{inverse_rate_value:.6f}",
                                "rate_value": inverse_rate_value,
                                "change": change,  # 방향이 반대가 되어야 하지만 여기서는 간단히 처리
                                "change_percent": change_pct,
                                "is_direct": False  # 역환율
                            })
                
                except Exception as e:
                    logger.error(f"환율 데이터 추출 중 오류: {str(e)}")
            
            # 결과가 없는 경우 처리
            if not exchange_rates:
                logger.warning(f"{currency_code} 관련 환율 정보를 찾을 수 없습니다.")
                return {
                    "status": "error",
                    "message": f"{currency} 관련 환율 정보를 찾을 수 없습니다.",
                    "currency": currency
                }
            
            # 결과 정리 (직접 환율 우선)
            direct_rates = [rate for rate in exchange_rates if rate["is_direct"]]
            if direct_rates:
                main_rate = direct_rates[0]
            else:
                main_rate = exchange_rates[0]
            
            # 현재 시각
            current_time = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
            
            # 결과를 저장
            filepath = None
            if save_results:
                # 저장 디렉토리 확인 및 생성
                os.makedirs(save_path, exist_ok=True)
                
                # CSV 파일로 저장
                timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
                filename = f"환율_{currency_code}_{timestamp}.csv"
                filepath = os.path.join(save_path, filename)
                
                with open(filepath, 'w', newline='', encoding='utf-8') as f:
                    writer = csv.writer(f)
                    writer.writerow(['통화쌍', '기준통화', '호가통화', '환율', '변동', '변동률', '직접환율여부', '조회시각'])
                    
                    for rate in exchange_rates:
                        writer.writerow([
                            rate["pair"],
                            rate["base_currency"],
                            rate["quote_currency"],
                            rate["rate"],
                            rate["change"],
                            rate["change_percent"],
                            '직접환율' if rate["is_direct"] else '역환율',
                            current_time
                        ])
                
                logger.info(f"환율 정보가 {filepath}에 저장되었습니다.")
            
            # 계산된 결과
            converted_amount = amount * main_rate["rate_value"]
            
            # 메시지 구성
            if main_rate["is_direct"]:
                # 직접 환율 (예: KRW/USD)
                message = f"{amount} {main_rate['base_currency']} = {converted_amount:.2f} {main_rate['quote_currency']} (환율: {main_rate['rate']})"
            else:
                # 역환율 (예: USD/KRW의 역)
                message = f"{amount} {main_rate['base_currency']} = {converted_amount:.2f} {main_rate['quote_currency']} (환율: {main_rate['rate']})"
            
            message += f"\n(변동: {main_rate['change']}, {main_rate['change_percent']})"
            message += f"\n조회 시각: {current_time}"
            
            # 다른 통화들에 대한 정보도 추가
            if len(exchange_rates) > 1:
                message += "\n\n다른 통화와의 환율:"
                for i, rate in enumerate(exchange_rates[1:5], 1):  # 최대 4개 추가 통화까지만 표시
                    conv_amount = amount * rate["rate_value"]
                    message += f"\n{amount} {rate['base_currency']} = {conv_amount:.2f} {rate['quote_currency']} (환율: {rate['rate']})"
                
                if len(exchange_rates) > 5:
                    message += f"\n... 외 {len(exchange_rates) - 5}개 통화"
            
            return {
                "status": "success",
                "message": message,
                "currency": currency,
                "currency_code": currency_code,
                "amount": amount,
                "exchange_rates": exchange_rates,
                "main_rate": main_rate,
                "converted_amount": converted_amount,
                "timestamp": current_time,
                "file_path": filepath
            }
            
        except Exception as e:
            error_msg = f"환율 조회 작업 실행 중 오류: {str(e)}"
            logger.error(error_msg)
            return {"status": "error", "message": error_msg}
            
        finally:
            # 페이지 닫기
            page.close()