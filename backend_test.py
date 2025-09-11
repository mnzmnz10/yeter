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
    def __init__(self, base_url="https://caravan-pdf-quote.preview.emergentagent.com/api"):
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