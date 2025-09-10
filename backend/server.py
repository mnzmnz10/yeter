from fastapi import FastAPI, APIRouter, HTTPException, UploadFile, File, Form
from fastapi.middleware.cors import CORSMiddleware
from motor.motor_asyncio import AsyncIOMotorClient
from pydantic import BaseModel, Field
from typing import List, Optional, Dict, Any
from datetime import datetime, timezone
from decimal import Decimal
import os
import uuid
import pandas as pd
import requests
import logging
from pathlib import Path
from dotenv import load_dotenv
import io

# Load environment variables
ROOT_DIR = Path(__file__).parent
load_dotenv(ROOT_DIR / '.env')

# MongoDB connection
mongo_url = os.environ['MONGO_URL']
client = AsyncIOMotorClient(mongo_url)
db = client[os.environ['DB_NAME']]

# Create the main app
app = FastAPI(title="Karavan Elektrik Ekipmanları Fiyat Karşılaştırma API")

# Create a router with the /api prefix
api_router = APIRouter(prefix="/api")

# Configure CORS
app.add_middleware(
    CORSMiddleware,
    allow_credentials=True,
    allow_origins=os.environ.get('CORS_ORIGINS', '*').split(','),
    allow_methods=["*"],
    allow_headers=["*"],
)

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Pydantic Models
class Company(BaseModel):
    id: str = Field(default_factory=lambda: str(uuid.uuid4()))
    name: str
    created_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))

class CompanyCreate(BaseModel):
    name: str

class Product(BaseModel):
    id: str = Field(default_factory=lambda: str(uuid.uuid4()))
    name: str
    company_id: str
    list_price: Decimal
    discounted_price: Optional[Decimal] = None
    currency: str
    list_price_try: Optional[Decimal] = None
    discounted_price_try: Optional[Decimal] = None
    created_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))

class ProductCreate(BaseModel):
    name: str
    company_id: str
    list_price: Decimal
    discounted_price: Optional[Decimal] = None
    currency: str

class ProductMatch(BaseModel):
    id: str = Field(default_factory=lambda: str(uuid.uuid4()))
    product_name: str
    product_ids: List[str] = []
    created_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))

class ProductMatchCreate(BaseModel):
    product_name: str
    product_ids: List[str]

class ExchangeRate(BaseModel):
    currency: str
    rate_to_try: Decimal
    updated_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))

# Currency conversion service
class CurrencyService:
    def __init__(self):
        self.api_url = "https://api.exchangerate-api.com/v4/latest/TRY"
        self.rates_cache = {}
        self.last_update = None
    
    async def get_exchange_rates(self) -> Dict[str, Decimal]:
        """Get current exchange rates from API"""
        try:
            response = requests.get(self.api_url, timeout=10)
            response.raise_for_status()
            data = response.json()
            
            # Convert to rates from other currencies to TRY
            base_rates = data.get('rates', {})
            try_to_usd = base_rates.get('USD', 1)
            try_to_eur = base_rates.get('EUR', 1)
            
            # Calculate USD and EUR to TRY
            usd_to_try = Decimal('1') / Decimal(str(try_to_usd)) if try_to_usd else Decimal('1')
            eur_to_try = Decimal('1') / Decimal(str(try_to_eur)) if try_to_eur else Decimal('1')
            
            rates = {
                'USD': usd_to_try,
                'EUR': eur_to_try,
                'TRY': Decimal('1'),
                'GBP': Decimal('1') / Decimal(str(base_rates.get('GBP', 1))) if base_rates.get('GBP') else Decimal('1')
            }
            
            self.rates_cache = rates
            self.last_update = datetime.now(timezone.utc)
            
            # Save to database
            for currency, rate in rates.items():
                await db.exchange_rates.replace_one(
                    {'currency': currency},
                    {
                        'currency': currency,
                        'rate_to_try': float(rate),
                        'updated_at': self.last_update
                    },
                    upsert=True
                )
            
            logger.info(f"Exchange rates updated: {rates}")
            return rates
            
        except Exception as e:
            logger.error(f"Failed to fetch exchange rates: {e}")
            # Try to get from database as fallback
            rates_from_db = await db.exchange_rates.find().to_list(None)
            if rates_from_db:
                return {rate['currency']: Decimal(str(rate['rate_to_try'])) for rate in rates_from_db}
            
            # Default rates as fallback
            return {
                'USD': Decimal('27.5'),
                'EUR': Decimal('30.0'),
                'TRY': Decimal('1'),
                'GBP': Decimal('35.0')
            }
    
    async def convert_to_try(self, amount: Decimal, from_currency: str) -> Decimal:
        """Convert amount to Turkish Lira"""
        if from_currency.upper() == 'TRY':
            return amount
            
        rates = await self.get_exchange_rates()
        rate = rates.get(from_currency.upper(), Decimal('1'))
        return amount * rate

currency_service = CurrencyService()

# Excel parsing service
class ExcelService:
    @staticmethod
    def parse_excel_file(file_content: bytes) -> List[Dict[str, Any]]:
        """Parse Excel file and extract product data"""
        try:
            # Read Excel file
            df = pd.read_excel(io.BytesIO(file_content))
            
            # Expected columns: Ürün Adı, Liste Fiyatı, İndirimli Fiyat, Para Birimi
            # Try different column name variations
            column_mapping = {
                'ürün adı': 'product_name',
                'urun adi': 'product_name',
                'product name': 'product_name',
                'ürün': 'product_name',
                'ad': 'product_name',
                'liste fiyatı': 'list_price',
                'liste fiyati': 'list_price',
                'list price': 'list_price',
                'fiyat': 'list_price',
                'liste': 'list_price',
                'indirimli fiyat': 'discounted_price',
                'indirimli fiyati': 'discounted_price',
                'discounted price': 'discounted_price',
                'indirim': 'discounted_price',
                'para birimi': 'currency',
                'para birimi': 'currency',
                'currency': 'currency',
                'birim': 'currency',
                'döviz': 'currency'
            }
            
            # Normalize column names
            df.columns = df.columns.str.lower().str.strip()
            
            # Find and rename columns
            for col in df.columns:
                for mapping_key, mapping_value in column_mapping.items():
                    if mapping_key in col:
                        df = df.rename(columns={col: mapping_value})
                        break
            
            # Ensure required columns exist
            required_columns = ['product_name', 'list_price', 'currency']
            missing_columns = [col for col in required_columns if col not in df.columns]
            
            if missing_columns:
                raise ValueError(f"Missing required columns: {missing_columns}")
            
            # Clean and convert data
            products = []
            for _, row in df.iterrows():
                try:
                    product = {
                        'name': str(row['product_name']).strip(),
                        'list_price': float(row['list_price']) if pd.notna(row['list_price']) else 0,
                        'currency': str(row['currency']).strip().upper(),
                        'discounted_price': float(row['discounted_price']) if 'discounted_price' in row and pd.notna(row['discounted_price']) else None
                    }
                    
                    # Skip empty rows
                    if not product['name'] or len(str(product['name']).strip()) == 0 or product['list_price'] <= 0:
                        continue
                        
                    products.append(product)
                    
                except (ValueError, TypeError) as e:
                    logger.warning(f"Skipping invalid row: {e}")
                    continue
            
            return products
            
        except Exception as e:
            logger.error(f"Error parsing Excel file: {e}")
            raise HTTPException(status_code=400, detail=f"Excel dosyası işlenemedi: {str(e)}")

excel_service = ExcelService()

# API Routes

@api_router.get("/")
async def root():
    return {"message": "Karavan Elektrik Ekipmanları Fiyat Karşılaştırma API"}

@api_router.get("/exchange-rates")
async def get_exchange_rates():
    """Get current exchange rates"""
    try:
        rates = await currency_service.get_exchange_rates()
        return {
            "success": True,
            "rates": {k: float(v) for k, v in rates.items()},
            "updated_at": currency_service.last_update.isoformat() if currency_service.last_update else None
        }
    except Exception as e:
        logger.error(f"Error getting exchange rates: {e}")
        raise HTTPException(status_code=500, detail="Döviz kurları alınamadı")

@api_router.post("/companies", response_model=Company)
async def create_company(company: CompanyCreate):
    """Create a new company"""
    try:
        company_dict = {
            "id": str(uuid.uuid4()),
            "name": company.name,
            "created_at": datetime.now(timezone.utc)
        }
        
        result = await db.companies.insert_one(company_dict)
        return Company(**company_dict)
        
    except Exception as e:
        logger.error(f"Error creating company: {e}")
        raise HTTPException(status_code=500, detail="Firma oluşturulamadı")

@api_router.get("/companies", response_model=List[Company])
async def get_companies():
    """Get all companies"""
    try:
        companies = await db.companies.find().to_list(None)
        return [Company(**company) for company in companies]
    except Exception as e:
        logger.error(f"Error getting companies: {e}")
        raise HTTPException(status_code=500, detail="Firmalar getirilemedi")

@api_router.delete("/companies/{company_id}")
async def delete_company(company_id: str):
    """Delete a company"""
    try:
        result = await db.companies.delete_one({"id": company_id})
        if result.deleted_count == 0:
            raise HTTPException(status_code=404, detail="Firma bulunamadı")
        
        # Also delete all products of this company
        await db.products.delete_many({"company_id": company_id})
        
        return {"success": True, "message": "Firma silindi"}
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error deleting company: {e}")
        raise HTTPException(status_code=500, detail="Firma silinemedi")

@api_router.post("/companies/{company_id}/upload-excel")
async def upload_excel(company_id: str, file: UploadFile = File(...)):
    """Upload Excel file for a company"""
    try:
        # Verify company exists
        company = await db.companies.find_one({"id": company_id})
        if not company:
            raise HTTPException(status_code=404, detail="Firma bulunamadı")
        
        # Check file type
        if not file.filename.endswith(('.xlsx', '.xls')):
            raise HTTPException(status_code=400, detail="Sadece Excel dosyaları (.xlsx, .xls) kabul edilir")
        
        # Read file content
        file_content = await file.read()
        
        # Parse Excel file
        products_data = excel_service.parse_excel_file(file_content)
        
        if not products_data:
            raise HTTPException(status_code=400, detail="Excel dosyasında geçerli ürün verisi bulunamadı")
        
        # Get current exchange rates
        await currency_service.get_exchange_rates()
        
        # Process and save products
        created_products = []
        for product_data in products_data:
            try:
                # Convert prices to TRY
                list_price_try = await currency_service.convert_to_try(
                    Decimal(str(product_data['list_price'])), 
                    product_data['currency']
                )
                
                discounted_price_try = None
                if product_data.get('discounted_price'):
                    discounted_price_try = await currency_service.convert_to_try(
                        Decimal(str(product_data['discounted_price'])), 
                        product_data['currency']
                    )
                
                product_dict = {
                    "id": str(uuid.uuid4()),
                    "name": product_data['name'],
                    "company_id": company_id,
                    "list_price": product_data['list_price'],
                    "discounted_price": product_data.get('discounted_price'),
                    "currency": product_data['currency'],
                    "list_price_try": float(list_price_try),
                    "discounted_price_try": float(discounted_price_try) if discounted_price_try else None,
                    "created_at": datetime.now(timezone.utc)
                }
                
                await db.products.insert_one(product_dict)
                created_products.append(Product(**product_dict))
                
            except Exception as e:
                logger.warning(f"Error processing product {product_data.get('name', 'Unknown')}: {e}")
                continue
        
        return {
            "success": True,
            "message": f"{len(created_products)} ürün başarıyla yüklendi",
            "products_count": len(created_products)
        }
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error uploading Excel file: {e}")
        raise HTTPException(status_code=500, detail=f"Excel dosyası yüklenemedi: {str(e)}")

@api_router.get("/products", response_model=List[Product])
async def get_products(company_id: Optional[str] = None):
    """Get all products, optionally filtered by company"""
    try:
        query = {}
        if company_id:
            query["company_id"] = company_id
            
        products = await db.products.find(query).to_list(None)
        return [Product(**product) for product in products]
    except Exception as e:
        logger.error(f"Error getting products: {e}")
        raise HTTPException(status_code=500, detail="Ürünler getirilemedi")

@api_router.get("/products/comparison")
async def get_products_comparison():
    """Get products grouped for comparison"""
    try:
        # Get all product matches
        matches = await db.product_matches.find().to_list(None)
        
        comparison_data = []
        for match in matches:
            # Get products for this match
            products = await db.products.find({"id": {"$in": match["product_ids"]}}).to_list(None)
            
            # Get company names
            company_ids = list(set([p["company_id"] for p in products]))
            companies = await db.companies.find({"id": {"$in": company_ids}}).to_list(None)
            company_names = {c["id"]: c["name"] for c in companies}
            
            # Format products with company names
            formatted_products = []
            for product in products:
                formatted_products.append({
                    **product,
                    "company_name": company_names.get(product["company_id"], "Unknown")
                })
            
            comparison_data.append({
                "id": match["id"],
                "product_name": match["product_name"],
                "products": formatted_products,
                "created_at": match["created_at"]
            })
        
        return {
            "success": True,
            "comparison_data": comparison_data
        }
        
    except Exception as e:
        logger.error(f"Error getting product comparison: {e}")
        raise HTTPException(status_code=500, detail="Ürün karşılaştırması getirilemedi")

@api_router.post("/product-matches", response_model=ProductMatch)
async def create_product_match(match: ProductMatchCreate):
    """Create a product match for comparison"""
    try:
        match_dict = {
            "id": str(uuid.uuid4()),
            "product_name": match.product_name,
            "product_ids": match.product_ids,
            "created_at": datetime.now(timezone.utc)
        }
        
        await db.product_matches.insert_one(match_dict)
        return ProductMatch(**match_dict)
        
    except Exception as e:
        logger.error(f"Error creating product match: {e}")
        raise HTTPException(status_code=500, detail="Ürün eşleştirmesi oluşturulamadı")

@api_router.get("/product-matches", response_model=List[ProductMatch])
async def get_product_matches():
    """Get all product matches"""
    try:
        matches = await db.product_matches.find().to_list(None)
        return [ProductMatch(**match) for match in matches]
    except Exception as e:
        logger.error(f"Error getting product matches: {e}")
        raise HTTPException(status_code=500, detail="Ürün eşleştirmeleri getirilemedi")

@api_router.delete("/product-matches/{match_id}")
async def delete_product_match(match_id: str):
    """Delete a product match"""
    try:
        result = await db.product_matches.delete_one({"id": match_id})
        if result.deleted_count == 0:
            raise HTTPException(status_code=404, detail="Ürün eşleştirmesi bulunamadı")
        
        return {"success": True, "message": "Ürün eşleştirmesi silindi"}
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error deleting product match: {e}")
        raise HTTPException(status_code=500, detail="Ürün eşleştirmesi silinemedi")

@api_router.post("/refresh-prices")
async def refresh_prices():
    """Refresh all product prices with current exchange rates"""
    try:
        # Get fresh exchange rates
        await currency_service.get_exchange_rates()
        
        # Get all products
        products = await db.products.find().to_list(None)
        updated_count = 0
        
        for product in products:
            try:
                if product['currency'] != 'TRY':
                    # Convert prices to TRY
                    list_price_try = await currency_service.convert_to_try(
                        Decimal(str(product['list_price'])), 
                        product['currency']
                    )
                    
                    discounted_price_try = None
                    if product.get('discounted_price'):
                        discounted_price_try = await currency_service.convert_to_try(
                            Decimal(str(product['discounted_price'])), 
                            product['currency']
                        )
                    
                    # Update product
                    await db.products.update_one(
                        {"id": product["id"]},
                        {
                            "$set": {
                                "list_price_try": float(list_price_try),
                                "discounted_price_try": float(discounted_price_try) if discounted_price_try else None
                            }
                        }
                    )
                    updated_count += 1
                    
            except Exception as e:
                logger.warning(f"Error updating product {product.get('name', 'Unknown')}: {e}")
                continue
        
        return {
            "success": True,
            "message": f"{updated_count} ürünün fiyatı güncellendi",
            "updated_count": updated_count
        }
        
    except Exception as e:
        logger.error(f"Error refreshing prices: {e}")
        raise HTTPException(status_code=500, detail="Fiyatlar güncellenemedi")

# Include the router in the main app
app.include_router(api_router)

@app.on_event("shutdown")
async def shutdown_db_client():
    client.close()

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8001)