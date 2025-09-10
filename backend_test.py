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
    def __init__(self, base_url="https://elektrofiyat.preview.emergentagent.com/api"):
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

    def test_exchange_rates(self):
        """Test exchange rates endpoint"""
        print("\n🔍 Testing Exchange Rates...")
        success, response = self.run_test(
            "Get Exchange Rates",
            "GET",
            "exchange-rates",
            200
        )
        
        if success and response:
            try:
                data = response.json()
                if data.get('success') and 'rates' in data:
                    rates = data['rates']
                    required_currencies = ['USD', 'EUR', 'TRY']
                    missing_currencies = [curr for curr in required_currencies if curr not in rates]
                    
                    if not missing_currencies:
                        self.log_test("Exchange Rates Format", True, f"All required currencies present: {list(rates.keys())}")
                        
                        # Check if rates are reasonable
                        usd_rate = rates.get('USD', 0)
                        eur_rate = rates.get('EUR', 0)
                        if 20 <= usd_rate <= 50 and 25 <= eur_rate <= 60:
                            self.log_test("Exchange Rates Values", True, f"USD: {usd_rate}, EUR: {eur_rate}")
                        else:
                            self.log_test("Exchange Rates Values", False, f"Rates seem unrealistic - USD: {usd_rate}, EUR: {eur_rate}")
                    else:
                        self.log_test("Exchange Rates Format", False, f"Missing currencies: {missing_currencies}")
                else:
                    self.log_test("Exchange Rates Format", False, "Invalid response format")
            except Exception as e:
                self.log_test("Exchange Rates Parsing", False, f"Error parsing response: {e}")
        
        return success

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

    def test_excel_upload(self, company_id):
        """Test Excel file upload functionality"""
        print("\n🔍 Testing Excel Upload...")
        
        if not company_id:
            self.log_test("Excel Upload", False, "No company ID available for testing")
            return False
        
        # Create a sample Excel file in memory
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
                "Upload Excel File",
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
                        self.log_test("Excel Upload Result", True, f"Uploaded {products_count} products")
                        return True
                    else:
                        self.log_test("Excel Upload Result", False, "Invalid response format")
                except Exception as e:
                    self.log_test("Excel Upload Response", False, f"Error parsing: {e}")
            
            return success
            
        except Exception as e:
            return self.log_test("Excel Upload", False, f"Error creating test file: {e}")

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

    def run_all_tests(self):
        """Run all backend tests"""
        print("🚀 Starting Karavan Elektrik Ekipmanları Backend API Tests")
        print(f"🌐 Testing against: {self.base_url}")
        print("=" * 80)
        
        try:
            # Test basic connectivity
            self.test_root_endpoint()
            
            # Test exchange rates
            self.test_exchange_rates()
            
            # Test company management
            company_id = self.test_company_management()
            
            # Test Excel upload (requires a company)
            if company_id:
                self.test_excel_upload(company_id)
            
            # Test products management
            self.test_products_management()
            
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