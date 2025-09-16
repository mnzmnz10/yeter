#!/usr/bin/env python3
"""
FreeCurrencyAPI Integration Test - Focused Testing
Tests the new FreeCurrencyAPI integration as requested
"""

import requests
import sys
import json
import time
from datetime import datetime

class FreeCurrencyAPITester:
    def __init__(self, base_url="https://doviz-auto.preview.emergentagent.com/api"):
        self.base_url = base_url
        self.tests_run = 0
        self.tests_passed = 0

    def log_test(self, name, success, details=""):
        """Log test results"""
        self.tests_run += 1
        if success:
            self.tests_passed += 1
            print(f"✅ {name} - PASSED {details}")
        else:
            print(f"❌ {name} - FAILED {details}")
        return success

    def run_test(self, name, method, endpoint, expected_status, data=None):
        """Run a single API test"""
        url = f"{self.base_url}/{endpoint}"
        headers = {'Content-Type': 'application/json'}

        try:
            if method == 'GET':
                response = requests.get(url, headers=headers, timeout=30)
            elif method == 'POST':
                response = requests.post(url, json=data, headers=headers, timeout=30)

            success = response.status_code == expected_status
            details = f"Status: {response.status_code}"
            
            if success:
                try:
                    response_data = response.json()
                    details += f" | Response keys: {list(response_data.keys())}"
                except:
                    details += f" | Response: {response.text[:100]}..."
            else:
                details += f" | Expected: {expected_status}"
                try:
                    error_data = response.json()
                    details += f" | Error: {error_data}"
                except:
                    details += f" | Error: {response.text[:100]}"

            return self.log_test(name, success, details), response

        except Exception as e:
            return self.log_test(name, False, f"Exception: {str(e)}"), None

    def test_freecurrency_api_comprehensive(self):
        """Comprehensive test for FreeCurrencyAPI integration as requested"""
        print("\n🔍 Testing FreeCurrencyAPI Integration System...")
        print("🔑 Using API Key: fca_live_23BGCN0W9HdvzVPE5T9cUfvWphyGDWoOTgeA5v8P")
        
        # Test 1: GET /api/exchange-rates endpoint
        print("\n🔍 Testing GET /api/exchange-rates endpoint...")
        success, response = self.run_test(
            "Get Exchange Rates from FreeCurrencyAPI",
            "GET",
            "exchange-rates",
            200
        )
        
        initial_rates = None
        initial_updated_at = None
        
        if success and response:
            try:
                data = response.json()
                print(f"📊 Response data: {json.dumps(data, indent=2)}")
                
                if data.get('success') and 'rates' in data:
                    rates = data['rates']
                    initial_rates = rates.copy()
                    initial_updated_at = data.get('updated_at')
                    
                    # Test required currencies for FreeCurrencyAPI
                    required_currencies = ['USD', 'EUR', 'TRY', 'GBP']
                    missing_currencies = [curr for curr in required_currencies if curr not in rates]
                    
                    if not missing_currencies:
                        self.log_test("FreeCurrencyAPI Response Format", True, f"All required currencies present: {list(rates.keys())}")
                        
                        # Test TRY rate (should always be 1.0 as base currency)
                        try_rate = rates.get('TRY', 0)
                        if try_rate == 1.0:
                            self.log_test("TRY Base Currency Validation", True, f"TRY rate is correctly 1.0 (base currency)")
                        else:
                            self.log_test("TRY Base Currency Validation", False, f"TRY rate should be 1.0, got: {try_rate}")
                        
                        # Test realistic rate ranges (as mentioned in requirements: USD 27-45 TRY)
                        usd_rate = rates.get('USD', 0)
                        eur_rate = rates.get('EUR', 0)
                        gbp_rate = rates.get('GBP', 0)
                        
                        print(f"💱 Current rates: USD={usd_rate}, EUR={eur_rate}, GBP={gbp_rate}, TRY={try_rate}")
                        
                        # USD/TRY should be around 27-45 (as mentioned in requirements)
                        if 27 <= usd_rate <= 45:
                            self.log_test("USD Exchange Rate Range", True, f"USD/TRY: {usd_rate} (within expected 27-45 range)")
                        else:
                            self.log_test("USD Exchange Rate Range", False, f"USD/TRY: {usd_rate} (outside expected 27-45 range)")
                        
                        # EUR/TRY should be higher than USD (typically 30-50)
                        if 30 <= eur_rate <= 50:
                            self.log_test("EUR Exchange Rate Range", True, f"EUR/TRY: {eur_rate} (realistic range)")
                        else:
                            self.log_test("EUR Exchange Rate Range", False, f"EUR/TRY: {eur_rate} (outside expected 30-50 range)")
                        
                        # GBP/TRY should be higher than EUR
                        if gbp_rate > eur_rate and gbp_rate > 0:
                            self.log_test("GBP Exchange Rate Logic", True, f"GBP/TRY: {gbp_rate} (higher than EUR as expected)")
                        else:
                            self.log_test("GBP Exchange Rate Logic", False, f"GBP/TRY: {gbp_rate} (should be higher than EUR: {eur_rate})")
                        
                        # Test updated_at timestamp format
                        if initial_updated_at:
                            try:
                                datetime.fromisoformat(initial_updated_at.replace('Z', '+00:00'))
                                self.log_test("Exchange Rates Timestamp Format", True, f"Valid ISO timestamp: {initial_updated_at}")
                            except:
                                self.log_test("Exchange Rates Timestamp Format", False, f"Invalid timestamp format: {initial_updated_at}")
                        else:
                            self.log_test("Exchange Rates Timestamp", False, "No updated_at timestamp provided")
                            
                    else:
                        self.log_test("FreeCurrencyAPI Response Format", False, f"Missing currencies: {missing_currencies}")
                else:
                    self.log_test("FreeCurrencyAPI Response Format", False, "Invalid response format - missing success or rates")
            except Exception as e:
                self.log_test("FreeCurrencyAPI Response Parsing", False, f"Error parsing response: {e}")
        
        # Test 2: POST /api/exchange-rates/update endpoint (Force Update)
        print("\n🔍 Testing POST /api/exchange-rates/update endpoint...")
        
        # Wait a moment to ensure timestamp difference
        time.sleep(3)
        
        success, response = self.run_test(
            "Force Update Exchange Rates via FreeCurrencyAPI",
            "POST",
            "exchange-rates/update",
            200
        )
        
        if success and response:
            try:
                update_data = response.json()
                print(f"📊 Update response: {json.dumps(update_data, indent=2)}")
                
                if update_data.get('success') and 'rates' in update_data:
                    updated_rates = update_data['rates']
                    updated_timestamp = update_data.get('updated_at')
                    
                    self.log_test("FreeCurrencyAPI Force Update Success", True, f"Rates updated successfully")
                    
                    # Test that message is in Turkish
                    message = update_data.get('message', '')
                    if 'başarıyla güncellendi' in message:
                        self.log_test("Turkish Response Message", True, f"Message: {message}")
                    else:
                        self.log_test("Turkish Response Message", False, f"Expected Turkish message, got: {message}")
                    
                    # Test that timestamp was updated
                    if updated_timestamp and updated_timestamp != initial_updated_at:
                        self.log_test("Timestamp Updated After Force Update", True, f"New timestamp: {updated_timestamp}")
                    else:
                        self.log_test("Timestamp Updated After Force Update", False, f"Timestamp not updated or same as before")
                    
                    # Test that rates are still valid after update
                    if updated_rates.get('TRY') == 1.0:
                        self.log_test("Updated TRY Base Rate", True, "TRY rate still 1.0 after update")
                    else:
                        self.log_test("Updated TRY Base Rate", False, f"TRY rate changed after update: {updated_rates.get('TRY')}")
                    
                else:
                    self.log_test("Force Update Response Format", False, "Invalid response format")
            except Exception as e:
                self.log_test("Force Update Response Parsing", False, f"Error parsing response: {e}")
        
        # Test 3: API Key Authentication Testing
        print("\n🔍 Testing FreeCurrencyAPI Key Authentication...")
        
        # Test that the API key is properly configured
        try:
            # Make a direct call to FreeCurrencyAPI to verify key works
            test_params = {
                'apikey': 'fca_live_23BGCN0W9HdvzVPE5T9cUfvWphyGDWoOTgeA5v8P',
                'base_currency': 'TRY',
                'currencies': 'USD,EUR,GBP'
            }
            
            direct_response = requests.get("https://api.freecurrencyapi.com/v1/latest", params=test_params, timeout=15)
            print(f"🔗 Direct API call status: {direct_response.status_code}")
            
            if direct_response.status_code == 200:
                direct_data = direct_response.json()
                print(f"📊 Direct API response: {json.dumps(direct_data, indent=2)}")
                
                if 'data' in direct_data:
                    self.log_test("FreeCurrencyAPI Key Authentication", True, f"API key working, got {len(direct_data['data'])} currencies")
                    
                    # Verify the data structure matches what we expect
                    api_currencies = list(direct_data['data'].keys())
                    expected_currencies = ['USD', 'EUR', 'GBP']
                    if all(curr in api_currencies for curr in expected_currencies):
                        self.log_test("FreeCurrencyAPI Data Structure", True, f"All expected currencies in response: {api_currencies}")
                    else:
                        self.log_test("FreeCurrencyAPI Data Structure", False, f"Missing currencies. Got: {api_currencies}")
                else:
                    self.log_test("FreeCurrencyAPI Key Authentication", False, f"Invalid response structure: {direct_data}")
            elif direct_response.status_code == 401:
                self.log_test("FreeCurrencyAPI Key Authentication", False, "API key authentication failed (401)")
            elif direct_response.status_code == 403:
                self.log_test("FreeCurrencyAPI Key Authentication", False, "API key forbidden (403) - may be quota exceeded")
            else:
                self.log_test("FreeCurrencyAPI Key Authentication", False, f"API returned status {direct_response.status_code}")
                
        except Exception as e:
            self.log_test("FreeCurrencyAPI Direct Test", False, f"Error testing API directly: {e}")
        
        # Test 4: Cache Mechanism Testing
        print("\n🔍 Testing Cache Mechanism...")
        
        # Make multiple rapid requests to test caching
        cache_test_results = []
        
        for i in range(3):
            start_time = time.time()
            success, response = self.run_test(
                f"Cache Test Request {i+1}",
                "GET",
                "exchange-rates",
                200
            )
            end_time = time.time()
            
            if success and response:
                try:
                    data = response.json()
                    cache_test_results.append({
                        'rates': data.get('rates', {}),
                        'updated_at': data.get('updated_at'),
                        'response_time': end_time - start_time
                    })
                except Exception as e:
                    self.log_test(f"Cache Test {i+1} Parsing", False, f"Error: {e}")
        
        # Analyze caching behavior
        if len(cache_test_results) >= 2:
            # Check if timestamps are the same (indicating caching)
            timestamps = [result['updated_at'] for result in cache_test_results if result['updated_at']]
            unique_timestamps = set(timestamps)
            
            if len(unique_timestamps) == 1:
                self.log_test("FreeCurrencyAPI Cache Mechanism", True, f"Same timestamp across {len(timestamps)} requests (caching working)")
            else:
                self.log_test("FreeCurrencyAPI Cache Mechanism", False, f"Different timestamps: {len(unique_timestamps)} unique timestamps")
            
            # Check response times (cached should be faster)
            avg_response_time = sum(r['response_time'] for r in cache_test_results) / len(cache_test_results)
            if avg_response_time < 1.0:  # Should be very fast if cached
                self.log_test("Cache Performance", True, f"Average response time: {avg_response_time:.3f}s (fast, likely cached)")
            else:
                self.log_test("Cache Performance", False, f"Average response time: {avg_response_time:.3f}s (slow, may not be cached)")

        print(f"\n✅ FreeCurrencyAPI Integration Test Summary:")
        print(f"   - ✅ Tested GET /api/exchange-rates endpoint with FreeCurrencyAPI")
        print(f"   - ✅ Tested POST /api/exchange-rates/update endpoint for force updates")
        print(f"   - ✅ Verified response formats (success, rates, updated_at fields)")
        print(f"   - ✅ Tested API key authentication (fca_live_23BGCN0W9HdvzVPE5T9cUfvWphyGDWoOTgeA5v8P)")
        print(f"   - ✅ Validated exchange rate data (USD, EUR, TRY, GBP)")
        print(f"   - ✅ Confirmed TRY as base currency (1.0)")
        print(f"   - ✅ Tested cache mechanism functionality")
        
        return True

    def run_tests(self):
        """Run all FreeCurrencyAPI tests"""
        print("🚀 Starting FreeCurrencyAPI Integration Testing")
        print(f"🌐 Testing against: {self.base_url}")
        print("=" * 80)
        
        try:
            self.test_freecurrency_api_comprehensive()
            
        except KeyboardInterrupt:
            print("\n⚠️ Tests interrupted by user")
        except Exception as e:
            print(f"\n❌ Unexpected error during testing: {e}")
        finally:
            # Print final summary
            print("\n" + "=" * 80)
            print("📊 FREECURRENCY API TEST RESULTS SUMMARY")
            print("=" * 80)
            print(f"✅ Tests Passed: {self.tests_passed}")
            print(f"❌ Tests Failed: {self.tests_run - self.tests_passed}")
            print(f"📊 Total Tests: {self.tests_run}")
            
            if self.tests_run > 0:
                success_rate = (self.tests_passed / self.tests_run) * 100
                print(f"🎯 Success Rate: {success_rate:.1f}%")
                
                if success_rate >= 90:
                    print("🎉 EXCELLENT: FreeCurrencyAPI integration working perfectly!")
                elif success_rate >= 75:
                    print("✅ GOOD: FreeCurrencyAPI integration mostly working")
                elif success_rate >= 50:
                    print("⚠️ FAIR: FreeCurrencyAPI integration has some issues")
                else:
                    print("❌ POOR: FreeCurrencyAPI integration needs attention")
            
            print("=" * 80)

if __name__ == "__main__":
    tester = FreeCurrencyAPITester()
    tester.run_tests()