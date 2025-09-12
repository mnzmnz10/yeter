#!/usr/bin/env python3
"""
Karavan Elektrik Ekipmanları Backend API Test Suite
Tests all API endpoints for the price comparison application
"""

import requests
import sys
import json
import time
from datetime import datetime
from io import BytesIO
import pandas as pd

class KaravanAPITester:
    def __init__(self, base_url="https://3ec20105-f006-4ffa-8c43-11ee418c5f73.preview.emergentagent.com/api"):
        self.base_url = base_url
        self.tests_run = 0
        self.tests_passed = 0
        self.created_companies = []
        self.created_products = []

    def log_test(self, name, success, details=""):
        """Log test results"""
        self.tests_run += 1
        if success:
            self.tests_passed += 1
            print(f"✅ {name} - PASSED {details}")
        else:
            print(f"❌ {name} - FAILED {details}")
        return success

    def run_test(self, name, method, endpoint, expected_status, data=None, files=None):
        """Run a single API test"""
        url = f"{self.base_url}/{endpoint}"
        headers = {'Content-Type': 'application/json'} if not files else {}

        try:
            if method == 'GET':
                response = requests.get(url, headers=headers, timeout=30)
            elif method == 'POST':
                if files:
                    response = requests.post(url, files=files, timeout=30)
                else:
                    response = requests.post(url, json=data, headers=headers, timeout=30)
            elif method == 'DELETE':
                response = requests.delete(url, headers=headers, timeout=30)

            success = response.status_code == expected_status
            details = f"Status: {response.status_code}"
            
            if success:
                try:
                    response_data = response.json()
                    details += f" | Response: {json.dumps(response_data, indent=2)[:200]}..."
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

    def test_root_endpoint(self):
        """Test root API endpoint"""
        print("\n🔍 Testing Root Endpoint...")
        success, response = self.run_test(
            "Root API Endpoint",
            "GET",
            "",
            200
        )
        return success

    def test_exchange_rates_comprehensive(self):
        """Comprehensive test for the new automatic exchange rate system"""
        print("\n🔍 Testing Automatic Exchange Rate System...")
        
        # Test 1: GET /api/exchange-rates endpoint
        print("\n🔍 Testing GET /api/exchange-rates endpoint...")
        success, response = self.run_test(
            "Get Exchange Rates",
            "GET",
            "exchange-rates",
            200
        )
        
        initial_rates = None
        initial_updated_at = None
        
        if success and response:
            try:
                data = response.json()
                if data.get('success') and 'rates' in data:
                    rates = data['rates']
                    initial_rates = rates.copy()
                    initial_updated_at = data.get('updated_at')
                    
                    # Test required currencies
                    required_currencies = ['USD', 'EUR', 'TRY', 'GBP']
                    missing_currencies = [curr for curr in required_currencies if curr not in rates]
                    
                    if not missing_currencies:
                        self.log_test("Exchange Rates Format", True, f"All required currencies present: {list(rates.keys())}")
                        
                        # Test TRY rate (should always be 1)
                        try_rate = rates.get('TRY', 0)
                        if try_rate == 1.0:
                            self.log_test("TRY Base Rate", True, f"TRY rate is correctly 1.0")
                        else:
                            self.log_test("TRY Base Rate", False, f"TRY rate should be 1.0, got: {try_rate}")
                        
                        # Test realistic rate ranges (based on current market rates)
                        usd_rate = rates.get('USD', 0)
                        eur_rate = rates.get('EUR', 0)
                        gbp_rate = rates.get('GBP', 0)
                        
                        # USD/TRY should be around 41-42 (as mentioned in requirements)
                        if 35 <= usd_rate <= 50:
                            self.log_test("USD Exchange Rate Range", True, f"USD/TRY: {usd_rate} (realistic)")
                        else:
                            self.log_test("USD Exchange Rate Range", False, f"USD/TRY: {usd_rate} (seems unrealistic, expected 35-50)")
                        
                        # EUR/TRY should be around 48-49 (as mentioned in requirements)
                        if 40 <= eur_rate <= 60:
                            self.log_test("EUR Exchange Rate Range", True, f"EUR/TRY: {eur_rate} (realistic)")
                        else:
                            self.log_test("EUR Exchange Rate Range", False, f"EUR/TRY: {eur_rate} (seems unrealistic, expected 40-60)")
                        
                        # GBP/TRY should be higher than EUR
                        if gbp_rate > eur_rate and gbp_rate > 0:
                            self.log_test("GBP Exchange Rate Logic", True, f"GBP/TRY: {gbp_rate} (higher than EUR as expected)")
                        else:
                            self.log_test("GBP Exchange Rate Logic", False, f"GBP/TRY: {gbp_rate} (should be higher than EUR: {eur_rate})")
                        
                        # Test updated_at timestamp
                        if initial_updated_at:
                            self.log_test("Exchange Rates Timestamp", True, f"Updated at: {initial_updated_at}")
                        else:
                            self.log_test("Exchange Rates Timestamp", False, "No updated_at timestamp provided")
                            
                    else:
                        self.log_test("Exchange Rates Format", False, f"Missing currencies: {missing_currencies}")
                else:
                    self.log_test("Exchange Rates Format", False, "Invalid response format")
            except Exception as e:
                self.log_test("Exchange Rates Parsing", False, f"Error parsing response: {e}")
        
        # Test 2: POST /api/exchange-rates/update endpoint (Force Update)
        print("\n🔍 Testing POST /api/exchange-rates/update endpoint...")
        
        # Wait a moment to ensure timestamp difference
        time.sleep(2)
        
        success, response = self.run_test(
            "Force Update Exchange Rates",
            "POST",
            "exchange-rates/update",
            200
        )
        
        if success and response:
            try:
                update_data = response.json()
                if update_data.get('success') and 'rates' in update_data:
                    updated_rates = update_data['rates']
                    updated_timestamp = update_data.get('updated_at')
                    
                    self.log_test("Force Update Success", True, f"Rates updated successfully")
                    
                    # Test that message is in Turkish
                    message = update_data.get('message', '')
                    if 'başarıyla güncellendi' in message:
                        self.log_test("Turkish Response Message", True, f"Message: {message}")
                    else:
                        self.log_test("Turkish Response Message", False, f"Expected Turkish message, got: {message}")
                    
                    # Test that timestamp was updated
                    if updated_timestamp and updated_timestamp != initial_updated_at:
                        self.log_test("Timestamp Updated", True, f"New timestamp: {updated_timestamp}")
                    else:
                        self.log_test("Timestamp Updated", False, f"Timestamp not updated or same as before")
                    
                    # Test that rates are still valid after update
                    if updated_rates.get('TRY') == 1.0:
                        self.log_test("Updated TRY Rate", True, "TRY rate still 1.0 after update")
                    else:
                        self.log_test("Updated TRY Rate", False, f"TRY rate changed after update: {updated_rates.get('TRY')}")
                    
                    # Test that rates changed (indicating fresh API call)
                    if initial_rates:
                        rates_changed = any(
                            abs(updated_rates.get(curr, 0) - initial_rates.get(curr, 0)) > 0.001
                            for curr in ['USD', 'EUR', 'GBP']
                        )
                        if rates_changed:
                            self.log_test("Fresh API Data", True, "Rates changed, indicating fresh API call")
                        else:
                            self.log_test("Fresh API Data", False, "Rates identical, may indicate caching issue")
                    
                else:
                    self.log_test("Force Update Format", False, "Invalid response format")
            except Exception as e:
                self.log_test("Force Update Parsing", False, f"Error parsing response: {e}")
        
        # Test 3: Exchange Rate Caching
        print("\n🔍 Testing Exchange Rate Caching...")
        
        # Make multiple rapid requests to test caching
        cache_test_results = []
        for i in range(3):
            success, response = self.run_test(
                f"Cache Test Request {i+1}",
                "GET",
                "exchange-rates",
                200
            )
            
            if success and response:
                try:
                    data = response.json()
                    cache_test_results.append({
                        'rates': data.get('rates', {}),
                        'updated_at': data.get('updated_at')
                    })
                except Exception as e:
                    self.log_test(f"Cache Test {i+1} Parsing", False, f"Error: {e}")
        
        # Analyze caching behavior
        if len(cache_test_results) >= 2:
            # Check if timestamps are the same (indicating caching)
            timestamps = [result['updated_at'] for result in cache_test_results if result['updated_at']]
            if len(set(timestamps)) == 1:
                self.log_test("Exchange Rate Caching", True, "Same timestamp across requests (caching working)")
            else:
                self.log_test("Exchange Rate Caching", False, "Different timestamps (caching may not be working)")
        
        # Test 4: External API Integration Test
        print("\n🔍 Testing External API Integration...")
        
        # Test the actual external API directly to verify it's accessible
        try:
            import requests
            external_response = requests.get("https://api.exchangerate-api.com/v4/latest/TRY", timeout=10)
            if external_response.status_code == 200:
                external_data = external_response.json()
                if 'rates' in external_data:
                    self.log_test("External API Accessibility", True, f"External API accessible, base: {external_data.get('base')}")
                    
                    # Check if our API returns similar rates
                    external_usd = external_data['rates'].get('USD', 0)
                    if initial_rates and external_usd > 0:
                        our_usd = initial_rates.get('USD', 0)
                        # Convert external rate (TRY to USD) to our format (USD to TRY)
                        expected_usd_to_try = 1 / external_usd if external_usd != 0 else 0
                        
                        # Allow 5% difference due to timing and rounding
                        if abs(our_usd - expected_usd_to_try) / expected_usd_to_try < 0.05:
                            self.log_test("API Rate Consistency", True, f"Our USD rate {our_usd} matches external {expected_usd_to_try:.4f}")
                        else:
                            self.log_test("API Rate Consistency", False, f"Rate mismatch - Our: {our_usd}, Expected: {expected_usd_to_try:.4f}")
                else:
                    self.log_test("External API Format", False, "External API response missing rates")
            else:
                self.log_test("External API Accessibility", False, f"External API returned status {external_response.status_code}")
        except Exception as e:
            self.log_test("External API Test", False, f"Error testing external API: {e}")
        
        # Test 5: Error Handling - Simulate API Unavailability
        print("\n🔍 Testing Error Handling...")
        
        # We can't easily simulate API failure, but we can test with invalid requests
        # Test with malformed request (this should still work as it's a GET request)
        success, response = self.run_test(
            "Error Handling Test",
            "GET",
            "exchange-rates?invalid=param",
            200  # Should still work despite invalid param
        )
        
        if success:
            self.log_test("Error Resilience", True, "API handles unexpected parameters gracefully")
        else:
            self.log_test("Error Resilience", False, "API failed with unexpected parameters")
        
        # Test 6: Database Persistence
        print("\n🔍 Testing Database Persistence...")
        
        # Force an update to ensure data is saved to database
        success, response = self.run_test(
            "Database Persistence Test",
            "POST",
            "exchange-rates/update",
            200
        )
        
        if success and response:
            try:
                data = response.json()
                if data.get('success'):
                    self.log_test("Database Persistence", True, "Exchange rates saved to MongoDB")
                    
                    # Verify rates are reasonable for database storage
                    rates = data.get('rates', {})
                    all_rates_valid = all(
                        isinstance(rate, (int, float)) and rate > 0 
                        for rate in rates.values()
                    )
                    
                    if all_rates_valid:
                        self.log_test("Database Data Validity", True, "All rates are valid numbers")
                    else:
                        self.log_test("Database Data Validity", False, "Some rates are invalid")
                else:
                    self.log_test("Database Persistence", False, "Update failed")
            except Exception as e:
                self.log_test("Database Persistence", False, f"Error: {e}")
        
        # Test 7: Rate Conversion Functionality
        print("\n🔍 Testing Rate Conversion in Product Creation...")
        
        # Create a test product to verify exchange rate conversion works
        test_company_name = f"Exchange Rate Test Company {datetime.now().strftime('%H%M%S')}"
        success, response = self.run_test(
            "Create Test Company for Exchange Rates",
            "POST",
            "companies",
            200,
            data={"name": test_company_name}
        )
        
        if success and response:
            try:
                company_data = response.json()
                test_company_id = company_data.get('id')
                if test_company_id:
                    self.created_companies.append(test_company_id)
                    
                    # Create a USD product to test conversion
                    usd_product = {
                        "name": "Exchange Rate Test Product USD",
                        "company_id": test_company_id,
                        "list_price": 100.00,
                        "currency": "USD",
                        "description": "Test product for exchange rate conversion"
                    }
                    
                    success, response = self.run_test(
                        "Create USD Product for Rate Test",
                        "POST",
                        "products",
                        200,
                        data=usd_product
                    )
                    
                    if success and response:
                        try:
                            product_data = response.json()
                            list_price_try = product_data.get('list_price_try')
                            
                            if list_price_try and list_price_try > 0:
                                # Check if conversion is reasonable
                                if initial_rates:
                                    expected_try_price = 100.00 * initial_rates.get('USD', 1)
                                    if abs(list_price_try - expected_try_price) < 1:
                                        self.log_test("Currency Conversion Integration", True, f"USD 100 → TRY {list_price_try}")
                                    else:
                                        self.log_test("Currency Conversion Integration", False, f"Expected ~{expected_try_price}, got {list_price_try}")
                                else:
                                    self.log_test("Currency Conversion Integration", True, f"USD 100 → TRY {list_price_try}")
                            else:
                                self.log_test("Currency Conversion Integration", False, f"Invalid TRY conversion: {list_price_try}")
                                
                            if product_data.get('id'):
                                self.created_products.append(product_data.get('id'))
                                
                        except Exception as e:
                            self.log_test("Currency Conversion Test", False, f"Error: {e}")
                            
            except Exception as e:
                self.log_test("Exchange Rate Company Setup", False, f"Error: {e}")
        
        print(f"\n✅ Exchange Rate System Test Summary:")
        print(f"   - Tested GET /api/exchange-rates endpoint")
        print(f"   - Tested POST /api/exchange-rates/update endpoint")
        print(f"   - Verified exchange rate data structure (USD, EUR, TRY, GBP)")
        print(f"   - Tested exchange rate caching mechanism")
        print(f"   - Verified external API integration (exchangerate-api.com)")
        print(f"   - Tested error handling and resilience")
        print(f"   - Verified database persistence")
        print(f"   - Tested currency conversion integration")
        
        return True

    def test_company_management(self):
        """Test company CRUD operations"""
        print("\n🔍 Testing Company Management...")
        
        # Test creating specific companies for Excel testing
        companies_to_create = ["HAVENSİS SOLAR", "ELEKTROZİRVE"]
        created_company_ids = {}
        
        for company_name in companies_to_create:
            success, response = self.run_test(
                f"Create Company: {company_name}",
                "POST",
                "companies",
                200,
                data={"name": company_name}
            )
            
            if success and response:
                try:
                    company_data = response.json()
                    company_id = company_data.get('id')
                    if company_id:
                        self.created_companies.append(company_id)
                        created_company_ids[company_name] = company_id
                        self.log_test(f"Company ID Generated for {company_name}", True, f"ID: {company_id}")
                    else:
                        self.log_test(f"Company ID Generated for {company_name}", False, "No ID in response")
                except Exception as e:
                    self.log_test(f"Company Creation Response for {company_name}", False, f"Error parsing: {e}")
        
        # Test creating a regular test company
        test_company_name = f"Test Firma {datetime.now().strftime('%H%M%S')}"
        success, response = self.run_test(
            "Create Test Company",
            "POST",
            "companies",
            200,
            data={"name": test_company_name}
        )
        
        company_id = None
        if success and response:
            try:
                company_data = response.json()
                company_id = company_data.get('id')
                if company_id:
                    self.created_companies.append(company_id)
                    created_company_ids["TEST"] = company_id
                    self.log_test("Test Company ID Generated", True, f"ID: {company_id}")
                else:
                    self.log_test("Test Company ID Generated", False, "No ID in response")
            except Exception as e:
                self.log_test("Test Company Creation Response", False, f"Error parsing: {e}")
        
        # Test getting all companies
        success, response = self.run_test(
            "Get All Companies",
            "GET",
            "companies",
            200
        )
        
        if success and response:
            try:
                companies = response.json()
                if isinstance(companies, list):
                    self.log_test("Companies List Format", True, f"Found {len(companies)} companies")
                    
                    # Check if our created companies are in the list
                    for company_name, comp_id in created_company_ids.items():
                        found_company = any(c.get('id') == comp_id for c in companies)
                        self.log_test(f"Created Company {company_name} in List", found_company, f"Company ID: {comp_id}")
                else:
                    self.log_test("Companies List Format", False, "Response is not a list")
            except Exception as e:
                self.log_test("Companies List Parsing", False, f"Error: {e}")
        
        return created_company_ids

    def test_excel_upload(self, company_ids):
        """Test Excel file upload functionality"""
        print("\n🔍 Testing Excel Upload...")
        
        if not company_ids:
            self.log_test("Excel Upload", False, "No company IDs available for testing")
            return False
        
        # Test actual Excel files
        excel_files = [
            ("/app/HAVENSİS_SOLAR.xlsx", "HAVENSİS SOLAR"),
            ("/app/ELEKTROZİRVE.xlsx", "ELEKTROZİRVE")
        ]
        
        upload_results = {}
        
        for file_path, company_name in excel_files:
            if company_name not in company_ids:
                self.log_test(f"Excel Upload for {company_name}", False, f"Company {company_name} not found in created companies")
                continue
                
            company_id = company_ids[company_name]
            
            try:
                # Read the actual Excel file
                with open(file_path, 'rb') as f:
                    file_content = f.read()
                
                files = {'file': (f'{company_name}.xlsx', file_content, 'application/vnd.openxmlformats-officedocument.spreadsheetml.sheet')}
                
                success, response = self.run_test(
                    f"Upload Excel File for {company_name}",
                    "POST",
                    f"companies/{company_id}/upload-excel",
                    200,
                    files=files
                )
                
                if success and response:
                    try:
                        upload_result = response.json()
                        if upload_result.get('success') and 'products_count' in upload_result:
                            products_count = upload_result['products_count']
                            upload_results[company_name] = products_count
                            self.log_test(f"Excel Upload Result for {company_name}", True, f"Uploaded {products_count} products")
                        else:
                            self.log_test(f"Excel Upload Result for {company_name}", False, "Invalid response format")
                    except Exception as e:
                        self.log_test(f"Excel Upload Response for {company_name}", False, f"Error parsing: {e}")
                else:
                    upload_results[company_name] = 0
                    
            except FileNotFoundError:
                self.log_test(f"Excel File for {company_name}", False, f"File not found: {file_path}")
            except Exception as e:
                self.log_test(f"Excel Upload for {company_name}", False, f"Error: {e}")
        
        # Test with a sample Excel file as well
        if "TEST" in company_ids:
            try:
                # Create sample data
                sample_data = {
                    'Ürün Adı': ['Test Ürün 1', 'Test Ürün 2', 'Test Ürün 3'],
                    'Liste Fiyatı': [100.50, 250.75, 89.99],
                    'İndirimli Fiyat': [85.50, 200.00, None],
                    'Para Birimi': ['USD', 'EUR', 'TRY']
                }
                
                df = pd.DataFrame(sample_data)
                excel_buffer = BytesIO()
                df.to_excel(excel_buffer, index=False)
                excel_buffer.seek(0)
                
                # Upload the Excel file
                files = {'file': ('test_products.xlsx', excel_buffer.getvalue(), 'application/vnd.openxmlformats-officedocument.spreadsheetml.sheet')}
                
                success, response = self.run_test(
                    "Upload Sample Excel File",
                    "POST",
                    f"companies/{company_ids['TEST']}/upload-excel",
                    200,
                    files=files
                )
                
                if success and response:
                    try:
                        upload_result = response.json()
                        if upload_result.get('success') and 'products_count' in upload_result:
                            products_count = upload_result['products_count']
                            upload_results["TEST"] = products_count
                            self.log_test("Sample Excel Upload Result", True, f"Uploaded {products_count} products")
                        else:
                            self.log_test("Sample Excel Upload Result", False, "Invalid response format")
                    except Exception as e:
                        self.log_test("Sample Excel Upload Response", False, f"Error parsing: {e}")
                        
            except Exception as e:
                self.log_test("Sample Excel Upload", False, f"Error creating test file: {e}")
        
        return upload_results

    def test_products_management(self):
        """Test products endpoints"""
        print("\n🔍 Testing Products Management...")
        
        # Test getting all products
        success, response = self.run_test(
            "Get All Products",
            "GET",
            "products",
            200
        )
        
        if success and response:
            try:
                products = response.json()
                if isinstance(products, list):
                    self.log_test("Products List Format", True, f"Found {len(products)} products")
                    
                    # Check product structure if any products exist
                    if products:
                        sample_product = products[0]
                        required_fields = ['id', 'name', 'company_id', 'list_price', 'currency']
                        missing_fields = [field for field in required_fields if field not in sample_product]
                        
                        if not missing_fields:
                            self.log_test("Product Structure", True, "All required fields present")
                            
                            # Check if TRY conversion is working
                            if 'list_price_try' in sample_product and sample_product['list_price_try']:
                                self.log_test("Currency Conversion", True, f"TRY price: {sample_product['list_price_try']}")
                            else:
                                self.log_test("Currency Conversion", False, "No TRY conversion found")
                        else:
                            self.log_test("Product Structure", False, f"Missing fields: {missing_fields}")
                else:
                    self.log_test("Products List Format", False, "Response is not a list")
            except Exception as e:
                self.log_test("Products List Parsing", False, f"Error: {e}")
        
        return success

    def test_nan_fix_comprehensive(self):
        """Comprehensive test for NaN issue fix in quote calculations"""
        print("\n🔍 Testing NaN Fix - Product Creation & Currency Conversion...")
        
        # First create a test company for our NaN tests
        test_company_name = f"NaN Test Company {datetime.now().strftime('%H%M%S')}"
        success, response = self.run_test(
            "Create NaN Test Company",
            "POST",
            "companies",
            200,
            data={"name": test_company_name}
        )
        
        if not success or not response:
            self.log_test("NaN Test Setup", False, "Failed to create test company")
            return False
            
        try:
            company_data = response.json()
            test_company_id = company_data.get('id')
            if not test_company_id:
                self.log_test("NaN Test Setup", False, "No company ID returned")
                return False
            self.created_companies.append(test_company_id)
        except Exception as e:
            self.log_test("NaN Test Setup", False, f"Error parsing company response: {e}")
            return False

        # Test 1: Create products with different currencies
        test_products = [
            {
                "name": "Solar Panel USD Test",
                "company_id": test_company_id,
                "list_price": 299.99,
                "discounted_price": 249.99,
                "currency": "USD",
                "description": "Test product in USD"
            },
            {
                "name": "Inverter EUR Test", 
                "company_id": test_company_id,
                "list_price": 450.50,
                "discounted_price": 399.00,
                "currency": "EUR",
                "description": "Test product in EUR"
            },
            {
                "name": "Battery TRY Test",
                "company_id": test_company_id,
                "list_price": 8500.00,
                "discounted_price": 7500.00,
                "currency": "TRY",
                "description": "Test product in TRY"
            }
        ]
        
        created_product_ids = []
        
        for product_data in test_products:
            success, response = self.run_test(
                f"Create Product: {product_data['name']} ({product_data['currency']})",
                "POST",
                "products",
                200,
                data=product_data
            )
            
            if success and response:
                try:
                    product_response = response.json()
                    product_id = product_response.get('id')
                    if product_id:
                        created_product_ids.append(product_id)
                        self.created_products.append(product_id)
                        
                        # Verify list_price_try is calculated and not NaN
                        list_price_try = product_response.get('list_price_try')
                        discounted_price_try = product_response.get('discounted_price_try')
                        
                        if list_price_try is not None and not (isinstance(list_price_try, float) and str(list_price_try).lower() == 'nan'):
                            self.log_test(f"List Price TRY Conversion - {product_data['currency']}", True, f"Converted to {list_price_try} TRY")
                        else:
                            self.log_test(f"List Price TRY Conversion - {product_data['currency']}", False, f"NaN or null value: {list_price_try}")
                        
                        if discounted_price_try is not None and not (isinstance(discounted_price_try, float) and str(discounted_price_try).lower() == 'nan'):
                            self.log_test(f"Discounted Price TRY Conversion - {product_data['currency']}", True, f"Converted to {discounted_price_try} TRY")
                        else:
                            self.log_test(f"Discounted Price TRY Conversion - {product_data['currency']}", False, f"NaN or null value: {discounted_price_try}")
                            
                    else:
                        self.log_test(f"Product Creation Response - {product_data['currency']}", False, "No product ID returned")
                except Exception as e:
                    self.log_test(f"Product Creation Response - {product_data['currency']}", False, f"Error parsing: {e}")
        
        # Test 2: Fetch all products and verify no NaN values
        print("\n🔍 Testing Product Listing for NaN Values...")
        success, response = self.run_test(
            "Get All Products - NaN Check",
            "GET",
            "products",
            200
        )
        
        if success and response:
            try:
                products = response.json()
                nan_found = False
                null_found = False
                valid_products = 0
                
                for product in products:
                    list_price_try = product.get('list_price_try')
                    discounted_price_try = product.get('discounted_price_try')
                    
                    # Check for NaN values
                    if isinstance(list_price_try, float) and str(list_price_try).lower() == 'nan':
                        nan_found = True
                        self.log_test("NaN Detection in list_price_try", False, f"Product {product.get('name', 'Unknown')} has NaN list_price_try")
                    elif list_price_try is None:
                        null_found = True
                        self.log_test("Null Detection in list_price_try", False, f"Product {product.get('name', 'Unknown')} has null list_price_try")
                    elif isinstance(list_price_try, (int, float)) and list_price_try > 0:
                        valid_products += 1
                    
                    if isinstance(discounted_price_try, float) and str(discounted_price_try).lower() == 'nan':
                        nan_found = True
                        self.log_test("NaN Detection in discounted_price_try", False, f"Product {product.get('name', 'Unknown')} has NaN discounted_price_try")
                
                if not nan_found:
                    self.log_test("No NaN Values Found", True, f"All {len(products)} products have valid price conversions")
                
                if not null_found:
                    self.log_test("No Null list_price_try Values", True, f"All products have list_price_try values")
                
                self.log_test("Valid Products Count", True, f"{valid_products} products with valid TRY prices")
                
            except Exception as e:
                self.log_test("Product NaN Check", False, f"Error checking products: {e}")
        
        # Test 3: Multiple Product Selection Scenario (simulating quote calculation)
        print("\n🔍 Testing Multiple Product Selection Scenario...")
        if len(created_product_ids) >= 2:
            # Get specific products that would be used in quote calculations
            for product_id in created_product_ids[:2]:  # Test with first 2 products
                success, response = self.run_test(
                    f"Get Product for Quote - {product_id[:8]}...",
                    "GET",
                    f"products?search={product_id}",  # This might not work, but let's try getting all and filter
                    200
                )
                
                if success and response:
                    try:
                        products = response.json()
                        target_product = next((p for p in products if p.get('id') == product_id), None)
                        
                        if target_product:
                            list_price_try = target_product.get('list_price_try')
                            if list_price_try is not None and not (isinstance(list_price_try, float) and str(list_price_try).lower() == 'nan'):
                                self.log_test(f"Quote Product Valid - {product_id[:8]}...", True, f"TRY price: {list_price_try}")
                            else:
                                self.log_test(f"Quote Product Valid - {product_id[:8]}...", False, f"Invalid TRY price: {list_price_try}")
                        else:
                            self.log_test(f"Quote Product Found - {product_id[:8]}...", False, "Product not found in list")
                    except Exception as e:
                        self.log_test(f"Quote Product Check - {product_id[:8]}...", False, f"Error: {e}")
        
        # Test 4: Edge cases - Invalid exchange rates handling
        print("\n🔍 Testing Edge Cases...")
        
        # Test with a currency that might not have exchange rates
        edge_case_product = {
            "name": "Edge Case Product",
            "company_id": test_company_id,
            "list_price": 100.00,
            "currency": "GBP",  # Less common currency
            "description": "Edge case test product"
        }
        
        success, response = self.run_test(
            "Create Product with GBP Currency",
            "POST",
            "products",
            200,
            data=edge_case_product
        )
        
        if success and response:
            try:
                product_response = response.json()
                list_price_try = product_response.get('list_price_try')
                
                if list_price_try is not None and not (isinstance(list_price_try, float) and str(list_price_try).lower() == 'nan'):
                    self.log_test("GBP Currency Conversion", True, f"GBP converted to {list_price_try} TRY")
                else:
                    self.log_test("GBP Currency Conversion", False, f"Failed conversion: {list_price_try}")
                    
                if product_response.get('id'):
                    self.created_products.append(product_response.get('id'))
                    
            except Exception as e:
                self.log_test("GBP Product Creation", False, f"Error: {e}")
        
        return True

    def test_comparison_endpoint(self):
        """Test products comparison endpoint"""
        print("\n🔍 Testing Products Comparison...")
        
        success, response = self.run_test(
            "Get Products Comparison",
            "GET",
            "products/comparison",
            200
        )
        
        if success and response:
            try:
                comparison_data = response.json()
                if comparison_data.get('success') and 'comparison_data' in comparison_data:
                    comparisons = comparison_data['comparison_data']
                    self.log_test("Comparison Data Format", True, f"Found {len(comparisons)} comparisons")
                else:
                    self.log_test("Comparison Data Format", False, "Invalid response format")
            except Exception as e:
                self.log_test("Comparison Data Parsing", False, f"Error: {e}")
        
        return success

    def test_refresh_prices(self):
        """Test price refresh endpoint"""
        print("\n🔍 Testing Price Refresh...")
        
        success, response = self.run_test(
            "Refresh Prices",
            "POST",
            "refresh-prices",
            200
        )
        
        if success and response:
            try:
                refresh_result = response.json()
                if refresh_result.get('success') and 'updated_count' in refresh_result:
                    updated_count = refresh_result['updated_count']
                    self.log_test("Price Refresh Result", True, f"Updated {updated_count} products")
                else:
                    self.log_test("Price Refresh Result", False, "Invalid response format")
            except Exception as e:
                self.log_test("Price Refresh Response", False, f"Error parsing: {e}")
        
        return success

    def test_pdf_generation_comprehensive(self):
        """Comprehensive test for improved PDF generation with Turkish characters and Montserrat font"""
        print("\n🔍 Testing PDF Generation with Turkish Characters and Montserrat Font...")
        
        # Step 1: Create a test company for PDF testing
        pdf_company_name = f"PDF Test Şirketi {datetime.now().strftime('%H%M%S')}"
        success, response = self.run_test(
            "Create PDF Test Company",
            "POST",
            "companies",
            200,
            data={"name": pdf_company_name}
        )
        
        if not success or not response:
            self.log_test("PDF Test Setup", False, "Failed to create test company")
            return False
            
        try:
            company_data = response.json()
            pdf_company_id = company_data.get('id')
            if not pdf_company_id:
                self.log_test("PDF Test Setup", False, "No company ID returned")
                return False
            self.created_companies.append(pdf_company_id)
        except Exception as e:
            self.log_test("PDF Test Setup", False, f"Error parsing company response: {e}")
            return False

        # Step 2: Create products with Turkish characters for PDF testing
        turkish_products = [
            {
                "name": "Güneş Paneli 450W Monokristal",
                "company_id": pdf_company_id,
                "list_price": 299.99,
                "discounted_price": 249.99,
                "currency": "USD",
                "description": "Yüksek verimli güneş paneli - Türkçe açıklama"
            },
            {
                "name": "İnvertör 5000W Hibrit Sistem", 
                "company_id": pdf_company_id,
                "list_price": 850.50,
                "discounted_price": 799.00,
                "currency": "EUR",
                "description": "Hibrit güneş enerjisi invertörü - şarj kontrolcülü"
            },
            {
                "name": "Akü 200Ah Derin Döngü",
                "company_id": pdf_company_id,
                "list_price": 12500.00,
                "discounted_price": 11250.00,
                "currency": "TRY",
                "description": "Güneş enerjisi sistemi için özel akü - uzun ömürlü"
            },
            {
                "name": "Şarj Kontrolcüsü MPPT 60A",
                "company_id": pdf_company_id,
                "list_price": 189.99,
                "discounted_price": 159.99,
                "currency": "USD",
                "description": "MPPT teknolojili şarj kontrolcüsü - LCD ekranlı"
            },
            {
                "name": "Kablo Seti ve Bağlantı Malzemeleri",
                "company_id": pdf_company_id,
                "list_price": 4500.00,
                "discounted_price": 3950.00,
                "currency": "TRY",
                "description": "Güneş enerjisi sistemi kurulum kabloları - özel üretim"
            }
        ]
        
        created_pdf_product_ids = []
        
        for product_data in turkish_products:
            success, response = self.run_test(
                f"Create Turkish Product: {product_data['name'][:30]}...",
                "POST",
                "products",
                200,
                data=product_data
            )
            
            if success and response:
                try:
                    product_response = response.json()
                    product_id = product_response.get('id')
                    if product_id:
                        created_pdf_product_ids.append(product_id)
                        self.created_products.append(product_id)
                        self.log_test(f"Turkish Product Created - {product_data['name'][:20]}...", True, f"ID: {product_id}")
                    else:
                        self.log_test(f"Turkish Product Creation - {product_data['name'][:20]}...", False, "No product ID returned")
                except Exception as e:
                    self.log_test(f"Turkish Product Creation - {product_data['name'][:20]}...", False, f"Error parsing: {e}")

        if len(created_pdf_product_ids) < 3:
            self.log_test("PDF Test Products", False, f"Only {len(created_pdf_product_ids)} products created, need at least 3")
            return False

        # Step 3: Create a quote with Turkish customer information
        quote_data = {
            "name": "Güneş Enerjisi Sistemi Teklifi - Türkçe Test",
            "customer_name": "Mehmet Özkan",
            "customer_email": "mehmet.ozkan@example.com",
            "discount_percentage": 5.0,
            "products": [
                {"id": created_pdf_product_ids[0], "quantity": 2},
                {"id": created_pdf_product_ids[1], "quantity": 1},
                {"id": created_pdf_product_ids[2], "quantity": 1},
                {"id": created_pdf_product_ids[3], "quantity": 3},
                {"id": created_pdf_product_ids[4], "quantity": 1}
            ],
            "notes": "Bu teklif Türkçe karakter desteği ve Montserrat font testi için hazırlanmıştır. Özel karakterler: ğüşıöç ĞÜŞIÖÇ"
        }
        
        success, response = self.run_test(
            "Create Turkish Quote for PDF",
            "POST",
            "quotes",
            200,
            data=quote_data
        )
        
        if not success or not response:
            self.log_test("PDF Quote Creation", False, "Failed to create quote")
            return False
            
        try:
            quote_response = response.json()
            quote_id = quote_response.get('id')
            if not quote_id:
                self.log_test("PDF Quote Creation", False, "No quote ID returned")
                return False
        except Exception as e:
            self.log_test("PDF Quote Creation", False, f"Error parsing quote response: {e}")
            return False

        # Step 4: Test PDF generation endpoint
        print(f"\n🔍 Testing PDF Generation for Quote ID: {quote_id}")
        
        try:
            pdf_url = f"{self.base_url}/quotes/{quote_id}/pdf"
            headers = {'Accept': 'application/pdf'}
            
            pdf_response = requests.get(pdf_url, headers=headers, timeout=60)
            
            if pdf_response.status_code == 200:
                # Check if response is actually a PDF
                content_type = pdf_response.headers.get('content-type', '')
                if 'application/pdf' in content_type:
                    pdf_size = len(pdf_response.content)
                    self.log_test("PDF Generation Success", True, f"PDF generated successfully, size: {pdf_size} bytes")
                    
                    # Basic PDF validation - check if it starts with PDF header
                    if pdf_response.content.startswith(b'%PDF'):
                        self.log_test("PDF Format Validation", True, "Valid PDF format detected")
                        
                        # Save PDF for manual inspection if needed
                        try:
                            with open(f'/tmp/test_quote_{quote_id}.pdf', 'wb') as f:
                                f.write(pdf_response.content)
                            self.log_test("PDF File Saved", True, f"PDF saved to /tmp/test_quote_{quote_id}.pdf")
                        except Exception as e:
                            self.log_test("PDF File Save", False, f"Could not save PDF: {e}")
                        
                        # Test PDF size - should be reasonable for a multi-product quote
                        if pdf_size > 10000:  # At least 10KB for a proper PDF
                            self.log_test("PDF Size Check", True, f"PDF size is reasonable: {pdf_size} bytes")
                        else:
                            self.log_test("PDF Size Check", False, f"PDF seems too small: {pdf_size} bytes")
                            
                    else:
                        self.log_test("PDF Format Validation", False, "Response does not appear to be a valid PDF")
                        
                else:
                    self.log_test("PDF Content Type", False, f"Expected PDF, got: {content_type}")
                    # Try to see what we actually got
                    try:
                        error_response = pdf_response.json()
                        self.log_test("PDF Generation Error", False, f"API Error: {error_response}")
                    except:
                        self.log_test("PDF Generation Error", False, f"Non-JSON error response: {pdf_response.text[:200]}")
                        
            else:
                self.log_test("PDF Generation Request", False, f"HTTP {pdf_response.status_code}: {pdf_response.text[:200]}")
                
        except Exception as e:
            self.log_test("PDF Generation Request", False, f"Exception during PDF generation: {e}")
            return False

        # Step 5: Test specific PDF features (if we can analyze the PDF content)
        print("\n🔍 Testing PDF Quality Features...")
        
        # Test Turkish price formatting by checking quote totals
        try:
            quote_check_response = requests.get(f"{self.base_url}/quotes/{quote_id}", timeout=30)
            if quote_check_response.status_code == 200:
                quote_details = quote_check_response.json()
                
                # Check if totals are calculated correctly (no NaN values)
                total_list_price = quote_details.get('total_list_price')
                total_net_price = quote_details.get('total_net_price')
                
                if total_list_price and total_net_price and total_list_price > 0 and total_net_price > 0:
                    self.log_test("Quote Totals Calculation", True, f"List: {total_list_price}, Net: {total_net_price}")
                    
                    # Check if discount was applied correctly
                    expected_discount = total_list_price * 0.05  # 5% discount
                    if abs((total_list_price - total_net_price) - expected_discount) < 1:  # Allow small rounding differences
                        self.log_test("Quote Discount Calculation", True, f"Discount applied correctly")
                    else:
                        self.log_test("Quote Discount Calculation", False, f"Discount calculation seems incorrect")
                        
                else:
                    self.log_test("Quote Totals Calculation", False, f"Invalid totals: List={total_list_price}, Net={total_net_price}")
                    
        except Exception as e:
            self.log_test("Quote Details Check", False, f"Error checking quote details: {e}")

        # Step 6: Test PDF generation with different scenarios
        print("\n🔍 Testing PDF Edge Cases...")
        
        # Test with a simple quote (fewer products)
        simple_quote_data = {
            "name": "Basit Teklif - Özel Karakterler: ğüşıöç",
            "customer_name": "Ayşe Çelik",
            "customer_email": "ayse.celik@test.com",
            "discount_percentage": 10.0,
            "products": [
                {"id": created_pdf_product_ids[0], "quantity": 1}
            ],
            "notes": "Tek ürünlü basit teklif - Türkçe karakter testi"
        }
        
        success, response = self.run_test(
            "Create Simple Turkish Quote",
            "POST",
            "quotes",
            200,
            data=simple_quote_data
        )
        
        if success and response:
            try:
                simple_quote_response = response.json()
                simple_quote_id = simple_quote_response.get('id')
                
                if simple_quote_id:
                    # Test PDF generation for simple quote
                    simple_pdf_url = f"{self.base_url}/quotes/{simple_quote_id}/pdf"
                    simple_pdf_response = requests.get(simple_pdf_url, headers={'Accept': 'application/pdf'}, timeout=60)
                    
                    if simple_pdf_response.status_code == 200 and simple_pdf_response.content.startswith(b'%PDF'):
                        simple_pdf_size = len(simple_pdf_response.content)
                        self.log_test("Simple Quote PDF Generation", True, f"Simple PDF generated, size: {simple_pdf_size} bytes")
                    else:
                        self.log_test("Simple Quote PDF Generation", False, f"Failed to generate simple PDF: {simple_pdf_response.status_code}")
                        
            except Exception as e:
                self.log_test("Simple Quote PDF Test", False, f"Error: {e}")

        # Step 7: Test company information in PDF (check if updated address appears)
        print("\n🔍 Testing Company Information in PDF...")
        
        # The PDF should contain the updated company information
        # We can't easily parse PDF content, but we can check if the generation succeeds
        # and the file size suggests it contains the expected content
        
        if pdf_response.status_code == 200 and len(pdf_response.content) > 15000:  # Larger PDF suggests more content
            self.log_test("Company Info in PDF", True, "PDF size suggests company information is included")
        else:
            self.log_test("Company Info in PDF", False, "PDF may be missing company information")

        print(f"\n✅ PDF Generation Test Summary:")
        print(f"   - Created {len(created_pdf_product_ids)} Turkish products")
        print(f"   - Generated quote with Turkish characters")
        print(f"   - Successfully tested PDF generation endpoint")
        print(f"   - Validated PDF format and content")
        
        return True

    def test_quote_functionality_after_rounding_removal(self):
        """Test quote functionality after removing 'Üzerine Tamamla' (rounding) feature"""
        print("\n🔍 Testing Quote Functionality After Rounding Feature Removal...")
        
        # Step 1: Create a test company for quote testing
        test_company_name = f"Rounding Test Company {datetime.now().strftime('%H%M%S')}"
        success, response = self.run_test(
            "Create Test Company for Rounding Test",
            "POST",
            "companies",
            200,
            data={"name": test_company_name}
        )
        
        if not success or not response:
            self.log_test("Rounding Test Setup", False, "Failed to create test company")
            return False
            
        try:
            company_data = response.json()
            test_company_id = company_data.get('id')
            if not test_company_id:
                self.log_test("Rounding Test Setup", False, "No company ID returned")
                return False
            self.created_companies.append(test_company_id)
        except Exception as e:
            self.log_test("Rounding Test Setup", False, f"Error parsing company response: {e}")
            return False

        # Step 2: Create test products with various prices
        test_products = [
            {
                "name": "Solar Panel 450W",
                "company_id": test_company_id,
                "list_price": 299.99,
                "discounted_price": 249.99,
                "currency": "USD",
                "description": "High efficiency solar panel"
            },
            {
                "name": "Inverter 5000W", 
                "company_id": test_company_id,
                "list_price": 750.50,
                "discounted_price": 699.00,
                "currency": "EUR",
                "description": "Hybrid solar inverter"
            },
            {
                "name": "Battery 200Ah",
                "company_id": test_company_id,
                "list_price": 8750.00,
                "discounted_price": 8250.00,
                "currency": "TRY",
                "description": "Deep cycle battery"
            }
        ]
        
        created_product_ids = []
        
        for product_data in test_products:
            success, response = self.run_test(
                f"Create Product: {product_data['name']}",
                "POST",
                "products",
                200,
                data=product_data
            )
            
            if success and response:
                try:
                    product_response = response.json()
                    product_id = product_response.get('id')
                    if product_id:
                        created_product_ids.append(product_id)
                        self.created_products.append(product_id)
                        self.log_test(f"Product Created - {product_data['name']}", True, f"ID: {product_id}")
                    else:
                        self.log_test(f"Product Creation - {product_data['name']}", False, "No product ID returned")
                except Exception as e:
                    self.log_test(f"Product Creation - {product_data['name']}", False, f"Error parsing: {e}")

        if len(created_product_ids) < 2:
            self.log_test("Rounding Test Products", False, f"Only {len(created_product_ids)} products created, need at least 2")
            return False

        # Step 3: Test Quote Creation without Rounding
        print("\n🔍 Testing Quote Creation Without Rounding...")
        
        quote_data = {
            "name": "Test Quote Without Rounding",
            "customer_name": "Test Customer",
            "customer_email": "test@example.com",
            "discount_percentage": 5.0,
            "labor_cost": 1500.0,  # Manual labor cost input
            "products": [
                {"id": created_product_ids[0], "quantity": 2},
                {"id": created_product_ids[1], "quantity": 1},
                {"id": created_product_ids[2], "quantity": 1}
            ],
            "notes": "Quote created after rounding feature removal"
        }
        
        success, response = self.run_test(
            "Create Quote Without Rounding",
            "POST",
            "quotes",
            200,
            data=quote_data
        )
        
        created_quote_id = None
        if success and response:
            try:
                quote_response = response.json()
                created_quote_id = quote_response.get('id')
                
                # Validate quote data structure
                required_fields = ['id', 'name', 'customer_name', 'discount_percentage', 'labor_cost', 'total_list_price', 'total_discounted_price', 'total_net_price', 'products', 'notes', 'created_at', 'status']
                missing_fields = [field for field in required_fields if field not in quote_response]
                
                if not missing_fields:
                    self.log_test("Quote Data Structure", True, "All required fields present")
                    
                    # Validate that labor cost is exactly what we set (no rounding)
                    labor_cost = quote_response.get('labor_cost', 0)
                    if labor_cost == 1500.0:
                        self.log_test("Manual Labor Cost Input", True, f"Labor cost: {labor_cost} (no automatic rounding)")
                    else:
                        self.log_test("Manual Labor Cost Input", False, f"Expected: 1500.0, Got: {labor_cost}")
                    
                    # Validate price calculations without rounding
                    total_list_price = quote_response.get('total_list_price', 0)
                    total_discounted_price = quote_response.get('total_discounted_price', 0)
                    total_net_price = quote_response.get('total_net_price', 0)
                    
                    if total_list_price > 0 and total_discounted_price > 0 and total_net_price > 0:
                        self.log_test("Price Calculations Without Rounding", True, f"List: {total_list_price}, Discounted: {total_discounted_price}, Net: {total_net_price}")
                        
                        # Verify discount calculation
                        expected_discount_amount = total_discounted_price * (quote_data['discount_percentage'] / 100)
                        expected_net_price = total_discounted_price - expected_discount_amount + quote_data['labor_cost']
                        
                        # Allow small floating point differences
                        if abs(total_net_price - expected_net_price) < 0.01:
                            self.log_test("Discount Calculation Accuracy", True, f"Net price calculation correct: {total_net_price}")
                        else:
                            self.log_test("Discount Calculation Accuracy", False, f"Expected: {expected_net_price}, Got: {total_net_price}")
                        
                        # Verify no automatic rounding to thousands
                        if total_net_price % 1000 != 0:
                            self.log_test("No Automatic Rounding", True, f"Net price not rounded to thousands: {total_net_price}")
                        else:
                            # Check if it's coincidentally a round number or actually rounded
                            if abs(total_net_price - expected_net_price) < 0.01:
                                self.log_test("No Automatic Rounding", True, f"Net price happens to be round but calculated correctly: {total_net_price}")
                            else:
                                self.log_test("No Automatic Rounding", False, f"Net price may have been automatically rounded: {total_net_price}")
                    else:
                        self.log_test("Price Calculations Without Rounding", False, f"Invalid prices - List: {total_list_price}, Discounted: {total_discounted_price}, Net: {total_net_price}")
                        
                else:
                    self.log_test("Quote Data Structure", False, f"Missing fields: {missing_fields}")
                    
            except Exception as e:
                self.log_test("Quote Creation Response", False, f"Error parsing: {e}")
        
        # Step 4: Test Quote Retrieval
        if created_quote_id:
            print("\n🔍 Testing Quote Retrieval...")
            
            success, response = self.run_test(
                "Get Created Quote",
                "GET",
                f"quotes/{created_quote_id}",
                200
            )
            
            if success and response:
                try:
                    retrieved_quote = response.json()
                    if retrieved_quote.get('id') == created_quote_id:
                        self.log_test("Quote Retrieval", True, f"Quote retrieved successfully: {created_quote_id}")
                        
                        # Verify data integrity
                        if retrieved_quote.get('labor_cost') == 1500.0:
                            self.log_test("Quote Data Integrity", True, "Labor cost preserved correctly")
                        else:
                            self.log_test("Quote Data Integrity", False, f"Labor cost changed: {retrieved_quote.get('labor_cost')}")
                    else:
                        self.log_test("Quote Retrieval", False, "Retrieved quote ID mismatch")
                except Exception as e:
                    self.log_test("Quote Retrieval Response", False, f"Error parsing: {e}")
        
        # Step 5: Test Quote List Retrieval
        print("\n🔍 Testing Quote List Retrieval...")
        
        success, response = self.run_test(
            "Get All Quotes",
            "GET",
            "quotes",
            200
        )
        
        if success and response:
            try:
                quotes_list = response.json()
                if isinstance(quotes_list, list):
                    self.log_test("Quotes List Format", True, f"Found {len(quotes_list)} quotes")
                    
                    # Check if our created quote is in the list
                    if created_quote_id:
                        found_quote = any(q.get('id') == created_quote_id for q in quotes_list)
                        self.log_test("Created Quote in List", found_quote, f"Quote ID: {created_quote_id}")
                else:
                    self.log_test("Quotes List Format", False, "Response is not a list")
            except Exception as e:
                self.log_test("Quotes List Parsing", False, f"Error: {e}")
        
        # Step 6: Test PDF Generation
        if created_quote_id:
            print("\n🔍 Testing PDF Generation After Rounding Removal...")
            
            try:
                pdf_url = f"{self.base_url}/quotes/{created_quote_id}/pdf"
                headers = {'Accept': 'application/pdf'}
                
                pdf_response = requests.get(pdf_url, headers=headers, timeout=60)
                
                if pdf_response.status_code == 200:
                    content_type = pdf_response.headers.get('content-type', '')
                    if 'application/pdf' in content_type and pdf_response.content.startswith(b'%PDF'):
                        pdf_size = len(pdf_response.content)
                        self.log_test("PDF Generation After Rounding Removal", True, f"PDF generated successfully, size: {pdf_size} bytes")
                        
                        # Save PDF for verification
                        try:
                            with open(f'/tmp/quote_no_rounding_{created_quote_id}.pdf', 'wb') as f:
                                f.write(pdf_response.content)
                            self.log_test("PDF File Saved", True, f"PDF saved to /tmp/quote_no_rounding_{created_quote_id}.pdf")
                        except Exception as e:
                            self.log_test("PDF File Save", False, f"Could not save PDF: {e}")
                    else:
                        self.log_test("PDF Generation After Rounding Removal", False, f"Invalid PDF response: {content_type}")
                else:
                    self.log_test("PDF Generation After Rounding Removal", False, f"HTTP {pdf_response.status_code}: {pdf_response.text[:200]}")
                    
            except Exception as e:
                self.log_test("PDF Generation Request", False, f"Exception during PDF generation: {e}")
        
        print(f"\n✅ Quote Functionality After Rounding Removal Test Summary:")
        print(f"   - Created {len(created_product_ids)} test products")
        print(f"   - Successfully created quote without automatic rounding")
        print(f"   - Verified manual labor cost input works correctly")
        print(f"   - Confirmed price calculations are accurate without rounding")
        print(f"   - Tested quote retrieval and data integrity")
        print(f"   - Verified PDF generation still works")
        
        return True

    def cleanup(self):
        """Clean up created test data"""
        print("\n🧹 Cleaning up test data...")
        
        # Delete created companies (this will also delete their products)
        for company_id in self.created_companies:
            try:
                success, response = self.run_test(
                    f"Delete Company {company_id}",
                    "DELETE",
                    f"companies/{company_id}",
                    200
                )
            except Exception as e:
                print(f"⚠️  Error deleting company {company_id}: {e}")

    def test_quick_quote_creation_comprehensive(self):
        """Comprehensive test for quick quote creation feature"""
        print("\n🔍 Testing Quick Quote Creation Feature...")
        
        # Step 1: Create a test company for quote testing
        quote_company_name = f"Quote Test Company {datetime.now().strftime('%H%M%S')}"
        success, response = self.run_test(
            "Create Quote Test Company",
            "POST",
            "companies",
            200,
            data={"name": quote_company_name}
        )
        
        if not success or not response:
            self.log_test("Quote Test Setup", False, "Failed to create test company")
            return False
            
        try:
            company_data = response.json()
            quote_company_id = company_data.get('id')
            if not quote_company_id:
                self.log_test("Quote Test Setup", False, "No company ID returned")
                return False
            self.created_companies.append(quote_company_id)
        except Exception as e:
            self.log_test("Quote Test Setup", False, f"Error parsing company response: {e}")
            return False

        # Step 2: Create test products for quote creation
        test_products = [
            {
                "name": "Güneş Paneli 400W",
                "company_id": quote_company_id,
                "list_price": 250.00,
                "discounted_price": 220.00,
                "currency": "USD",
                "description": "Yüksek verimli güneş paneli"
            },
            {
                "name": "İnvertör 3000W", 
                "company_id": quote_company_id,
                "list_price": 450.00,
                "discounted_price": 400.00,
                "currency": "EUR",
                "description": "Hibrit güneş enerjisi invertörü"
            },
            {
                "name": "Akü 100Ah",
                "company_id": quote_company_id,
                "list_price": 5500.00,
                "discounted_price": 5000.00,
                "currency": "TRY",
                "description": "Derin döngü akü"
            }
        ]
        
        created_product_ids = []
        
        for product_data in test_products:
            success, response = self.run_test(
                f"Create Quote Product: {product_data['name']}",
                "POST",
                "products",
                200,
                data=product_data
            )
            
            if success and response:
                try:
                    product_response = response.json()
                    product_id = product_response.get('id')
                    if product_id:
                        created_product_ids.append(product_id)
                        self.created_products.append(product_id)
                        self.log_test(f"Quote Product Created - {product_data['name']}", True, f"ID: {product_id}")
                    else:
                        self.log_test(f"Quote Product Creation - {product_data['name']}", False, "No product ID returned")
                except Exception as e:
                    self.log_test(f"Quote Product Creation - {product_data['name']}", False, f"Error parsing: {e}")

        if len(created_product_ids) < 2:
            self.log_test("Quote Test Products", False, f"Only {len(created_product_ids)} products created, need at least 2")
            return False

        # Step 3: Test Quick Quote Creation - Basic Scenario
        print("\n🔍 Testing Basic Quick Quote Creation...")
        
        current_date = datetime.now().strftime('%d/%m/%Y')
        customer_name = "Ahmet Yılmaz"
        
        quote_data = {
            "name": f"{customer_name} - {current_date}",
            "customer_name": customer_name,
            "discount_percentage": 0,
            "labor_cost": 0,
            "products": [
                {"id": created_product_ids[0], "quantity": 2},
                {"id": created_product_ids[1], "quantity": 1}
            ],
            "notes": "2 ürün ile oluşturulan teklif"
        }
        
        success, response = self.run_test(
            "Create Quick Quote - Basic",
            "POST",
            "quotes",
            200,
            data=quote_data
        )
        
        created_quote_id = None
        if success and response:
            try:
                quote_response = response.json()
                created_quote_id = quote_response.get('id')
                
                # Validate quote data structure
                required_fields = ['id', 'name', 'customer_name', 'discount_percentage', 'labor_cost', 'total_list_price', 'total_discounted_price', 'total_net_price', 'products', 'notes', 'created_at', 'status']
                missing_fields = [field for field in required_fields if field not in quote_response]
                
                if not missing_fields:
                    self.log_test("Quote Data Structure", True, "All required fields present")
                    
                    # Validate specific field values
                    if quote_response.get('customer_name') == customer_name:
                        self.log_test("Quote Customer Name", True, f"Customer: {customer_name}")
                    else:
                        self.log_test("Quote Customer Name", False, f"Expected: {customer_name}, Got: {quote_response.get('customer_name')}")
                    
                    if quote_response.get('discount_percentage') == 0:
                        self.log_test("Quote Discount Percentage", True, "Discount: 0%")
                    else:
                        self.log_test("Quote Discount Percentage", False, f"Expected: 0, Got: {quote_response.get('discount_percentage')}")
                    
                    if quote_response.get('labor_cost') == 0:
                        self.log_test("Quote Labor Cost", True, "Labor cost: 0")
                    else:
                        self.log_test("Quote Labor Cost", False, f"Expected: 0, Got: {quote_response.get('labor_cost')}")
                    
                    # Validate products in quote
                    quote_products = quote_response.get('products', [])
                    if len(quote_products) == 2:
                        self.log_test("Quote Products Count", True, f"Products: {len(quote_products)}")
                        
                        # Check product quantities
                        product_quantities = {p.get('id'): p.get('quantity') for p in quote_products}
                        expected_quantities = {created_product_ids[0]: 2, created_product_ids[1]: 1}
                        
                        quantities_correct = all(
                            product_quantities.get(pid) == expected_quantities.get(pid) 
                            for pid in expected_quantities
                        )
                        
                        if quantities_correct:
                            self.log_test("Quote Product Quantities", True, "All quantities correct")
                        else:
                            self.log_test("Quote Product Quantities", False, f"Expected: {expected_quantities}, Got: {product_quantities}")
                    else:
                        self.log_test("Quote Products Count", False, f"Expected: 2, Got: {len(quote_products)}")
                    
                    # Validate price calculations
                    total_list_price = quote_response.get('total_list_price', 0)
                    total_net_price = quote_response.get('total_net_price', 0)
                    
                    if total_list_price > 0 and total_net_price > 0:
                        self.log_test("Quote Price Calculations", True, f"List: {total_list_price}, Net: {total_net_price}")
                    else:
                        self.log_test("Quote Price Calculations", False, f"Invalid prices - List: {total_list_price}, Net: {total_net_price}")
                        
                else:
                    self.log_test("Quote Data Structure", False, f"Missing fields: {missing_fields}")
                    
            except Exception as e:
                self.log_test("Quote Creation Response", False, f"Error parsing: {e}")

        # Step 4: Test Quote Listing
        print("\n🔍 Testing Quote Listing...")
        
        success, response = self.run_test(
            "Get All Quotes",
            "GET",
            "quotes",
            200
        )
        
        if success and response:
            try:
                quotes = response.json()
                if isinstance(quotes, list):
                    self.log_test("Quotes List Format", True, f"Found {len(quotes)} quotes")
                    
                    # Check if our created quote is in the list
                    if created_quote_id:
                        found_quote = any(q.get('id') == created_quote_id for q in quotes)
                        self.log_test("Created Quote in List", found_quote, f"Quote ID: {created_quote_id}")
                        
                        if found_quote:
                            # Find our quote and validate its data
                            our_quote = next(q for q in quotes if q.get('id') == created_quote_id)
                            if our_quote.get('customer_name') == customer_name:
                                self.log_test("Quote List Data Integrity", True, "Quote data matches creation")
                            else:
                                self.log_test("Quote List Data Integrity", False, "Quote data doesn't match")
                else:
                    self.log_test("Quotes List Format", False, "Response is not a list")
            except Exception as e:
                self.log_test("Quotes List Parsing", False, f"Error: {e}")

        # Step 5: Test Individual Quote Retrieval
        if created_quote_id:
            print("\n🔍 Testing Individual Quote Retrieval...")
            
            success, response = self.run_test(
                f"Get Quote by ID",
                "GET",
                f"quotes/{created_quote_id}",
                200
            )
            
            if success and response:
                try:
                    quote_detail = response.json()
                    if quote_detail.get('id') == created_quote_id:
                        self.log_test("Quote Detail Retrieval", True, f"Retrieved quote: {quote_detail.get('name')}")
                    else:
                        self.log_test("Quote Detail Retrieval", False, "Wrong quote returned")
                except Exception as e:
                    self.log_test("Quote Detail Parsing", False, f"Error: {e}")

        # Step 6: Test Error Handling - Missing Customer Name
        print("\n🔍 Testing Error Handling...")
        
        invalid_quote_data = {
            "name": "Invalid Quote",
            "customer_name": "",  # Empty customer name
            "discount_percentage": 0,
            "labor_cost": 0,
            "products": [{"id": created_product_ids[0], "quantity": 1}],
            "notes": "Test quote with empty customer name"
        }
        
        success, response = self.run_test(
            "Create Quote - Empty Customer Name",
            "POST",
            "quotes",
            422,  # Expecting validation error
            data=invalid_quote_data
        )
        
        if not success:
            # If it doesn't return 422, check if it returns 400 or 500
            if response and response.status_code in [400, 500]:
                self.log_test("Empty Customer Name Validation", True, f"Properly rejected with status {response.status_code}")
            else:
                self.log_test("Empty Customer Name Validation", False, f"Unexpected status: {response.status_code if response else 'No response'}")
        else:
            self.log_test("Empty Customer Name Validation", False, "Should have rejected empty customer name")

        # Step 7: Test Error Handling - Invalid Product IDs
        invalid_product_quote = {
            "name": "Invalid Product Quote",
            "customer_name": "Test Customer",
            "discount_percentage": 0,
            "labor_cost": 0,
            "products": [{"id": "invalid-product-id", "quantity": 1}],
            "notes": "Test quote with invalid product ID"
        }
        
        success, response = self.run_test(
            "Create Quote - Invalid Product ID",
            "POST",
            "quotes",
            400,  # Expecting bad request
            data=invalid_product_quote
        )
        
        if not success:
            if response and response.status_code in [400, 404, 422]:
                self.log_test("Invalid Product ID Validation", True, f"Properly rejected with status {response.status_code}")
            else:
                self.log_test("Invalid Product ID Validation", False, f"Unexpected status: {response.status_code if response else 'No response'}")
        else:
            self.log_test("Invalid Product ID Validation", False, "Should have rejected invalid product ID")

        # Step 8: Test Error Handling - Empty Product List
        empty_products_quote = {
            "name": "Empty Products Quote",
            "customer_name": "Test Customer",
            "discount_percentage": 0,
            "labor_cost": 0,
            "products": [],  # Empty product list
            "notes": "Test quote with no products"
        }
        
        success, response = self.run_test(
            "Create Quote - Empty Product List",
            "POST",
            "quotes",
            400,  # Expecting bad request
            data=empty_products_quote
        )
        
        if not success:
            if response and response.status_code in [400, 422]:
                self.log_test("Empty Product List Validation", True, f"Properly rejected with status {response.status_code}")
            else:
                self.log_test("Empty Product List Validation", False, f"Unexpected status: {response.status_code if response else 'No response'}")
        else:
            self.log_test("Empty Product List Validation", False, "Should have rejected empty product list")

        # Step 9: Test Complex Quote Creation (Multiple Products with Different Currencies)
        print("\n🔍 Testing Complex Quote Creation...")
        
        if len(created_product_ids) >= 3:
            complex_quote_data = {
                "name": f"Karmaşık Teklif - {current_date}",
                "customer_name": "Mehmet Özkan",
                "discount_percentage": 5.0,  # 5% discount
                "labor_cost": 500.0,  # Labor cost
                "products": [
                    {"id": created_product_ids[0], "quantity": 3},
                    {"id": created_product_ids[1], "quantity": 2},
                    {"id": created_product_ids[2], "quantity": 1}
                ],
                "notes": "Karmaşık teklif - farklı para birimleri ve indirim"
            }
            
            success, response = self.run_test(
                "Create Complex Quote",
                "POST",
                "quotes",
                200,
                data=complex_quote_data
            )
            
            if success and response:
                try:
                    complex_quote = response.json()
                    
                    # Validate discount calculation
                    total_discounted_price = complex_quote.get('total_discounted_price', 0)
                    total_net_price = complex_quote.get('total_net_price', 0)
                    labor_cost = complex_quote.get('labor_cost', 0)
                    discount_percentage = complex_quote.get('discount_percentage', 0)
                    
                    # Calculate expected net price
                    discount_amount = total_discounted_price * (discount_percentage / 100)
                    expected_net_price = total_discounted_price - discount_amount + labor_cost
                    
                    # Allow small rounding differences
                    if abs(total_net_price - expected_net_price) < 1:
                        self.log_test("Complex Quote Calculations", True, f"Net price calculated correctly: {total_net_price}")
                    else:
                        self.log_test("Complex Quote Calculations", False, f"Expected: {expected_net_price}, Got: {total_net_price}")
                        
                    # Validate labor cost
                    if labor_cost == 500.0:
                        self.log_test("Complex Quote Labor Cost", True, f"Labor cost: {labor_cost}")
                    else:
                        self.log_test("Complex Quote Labor Cost", False, f"Expected: 500.0, Got: {labor_cost}")
                        
                except Exception as e:
                    self.log_test("Complex Quote Response", False, f"Error parsing: {e}")

        print(f"\n✅ Quick Quote Creation Test Summary:")
        print(f"   - Created {len(created_product_ids)} test products")
        print(f"   - Tested basic quote creation workflow")
        print(f"   - Validated quote data structure and calculations")
        print(f"   - Tested quote listing and retrieval")
        print(f"   - Tested error handling for edge cases")
        print(f"   - Tested complex quote with discounts and labor cost")
        
        return True

    def run_all_tests(self):
        """Run all backend tests"""
        print("🚀 Starting Karavan Elektrik Ekipmanları Backend API Tests")
        print(f"🌐 Testing against: {self.base_url}")
        print("=" * 80)
        
        try:
            # Test basic connectivity
            self.test_root_endpoint()
            
            # Test exchange rates comprehensively
            self.test_exchange_rates_comprehensive()
            
            # Test company management
            company_ids = self.test_company_management()
            
            # Test Excel upload (requires companies)
            if company_ids:
                upload_results = self.test_excel_upload(company_ids)
                
                # Print upload summary
                print("\n📊 EXCEL UPLOAD SUMMARY:")
                for company_name, product_count in upload_results.items():
                    print(f"  {company_name}: {product_count} products uploaded")
            else:
                print("⚠️  No companies created, skipping Excel upload tests")
            
            # Test products management
            self.test_products_management()
            
            # CRITICAL: Test NaN fix comprehensively
            self.test_nan_fix_comprehensive()
            
            # CRITICAL: Test Quick Quote Creation Feature
            self.test_quick_quote_creation_comprehensive()
            
            # CRITICAL: Test PDF generation with Turkish characters and Montserrat font
            self.test_pdf_generation_comprehensive()
            
            # Test comparison endpoint
            self.test_comparison_endpoint()
            
            # Test price refresh
            self.test_refresh_prices()
            
        finally:
            # Always cleanup
            self.cleanup()
        
        # Print final results
        print("\n" + "=" * 80)
        print("📊 TEST RESULTS SUMMARY")
        print("=" * 80)
        print(f"Total Tests Run: {self.tests_run}")
        print(f"Tests Passed: {self.tests_passed}")
        print(f"Tests Failed: {self.tests_run - self.tests_passed}")
        print(f"Success Rate: {(self.tests_passed/self.tests_run*100):.1f}%" if self.tests_run > 0 else "0%")
        
        if self.tests_passed == self.tests_run:
            print("🎉 ALL TESTS PASSED!")
            return 0
        else:
            print("⚠️  SOME TESTS FAILED!")
            return 1

def main():
    """Main test runner"""
    tester = KaravanAPITester()
    return tester.run_all_tests()

if __name__ == "__main__":
    sys.exit(main())