from fastapi import FastAPI, APIRouter, HTTPException, UploadFile, File, Form
from fastapi.responses import JSONResponse, StreamingResponse
from fastapi.middleware.cors import CORSMiddleware
from motor.motor_asyncio import AsyncIOMotorClient
from pydantic import BaseModel, Field
from typing import List, Optional, Dict, Any
from datetime import datetime, timezone
from decimal import Decimal, InvalidOperation
from bson import ObjectId
import os
import uuid
import pandas as pd
import requests
import logging
from io import BytesIO

from reportlab.lib.pagesizes import A4, letter
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
from reportlab.lib.units import cm, mm
from reportlab.lib import colors
from reportlab.platypus import SimpleDocTemplate, Paragraph, Spacer, Table, TableStyle, Image
from reportlab.lib.enums import TA_CENTER, TA_LEFT, TA_RIGHT
from reportlab.pdfbase import pdfmetrics
from reportlab.pdfbase.ttfonts import TTFont
from PIL import Image as PILImage
from pathlib import Path
from dotenv import load_dotenv
import io
import openpyxl
from openpyxl.styles import PatternFill

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
    category_id: Optional[str] = None
    description: Optional[str] = None
    image_url: Optional[str] = None
    list_price: Decimal
    discounted_price: Optional[Decimal] = None
    currency: str
    list_price_try: Optional[Decimal] = None
    discounted_price_try: Optional[Decimal] = None
    created_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))

class ProductCreate(BaseModel):
    name: str
    company_id: str
    category_id: Optional[str] = None
    description: Optional[str] = None
    image_url: Optional[str] = None
    list_price: Decimal
    discounted_price: Optional[Decimal] = None
    currency: str

class Category(BaseModel):
    id: str = Field(default_factory=lambda: str(uuid.uuid4()))
    name: str
    description: Optional[str] = None
    color: Optional[str] = None
    created_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))

class CategoryCreate(BaseModel):
    name: str
    description: Optional[str] = None
    color: Optional[str] = None

class QuoteCreate(BaseModel):
    name: str
    customer_name: Optional[str] = None
    customer_email: Optional[str] = None
    discount_percentage: float = 0
    products: List[Dict[str, Any]]  # Product objects with ID and quantity
    notes: Optional[str] = None

class QuoteResponse(BaseModel):
    id: str
    name: str
    customer_name: Optional[str] = None
    customer_email: Optional[str] = None
    discount_percentage: float
    total_list_price: float
    total_discounted_price: float 
    total_net_price: float
    products: List[Dict[str, Any]]
    notes: Optional[str] = None
    created_at: str
    status: str = "active"

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

# Database helper function
async def get_db():
    """Get database connection"""
    return db

# Color-based Excel parsing service
class ColorBasedExcelService:
    @staticmethod
    def detect_color_category(fill):
        """Detect color category from cell fill"""
        if not fill or not hasattr(fill, 'start_color'):
            return 'NONE'
            
        color = fill.start_color
        
        # RGB renk kontrolü
        if hasattr(color, 'rgb') and color.rgb:
            try:
                rgb = str(color.rgb).upper()
                
                # Debug için
                logger.debug(f"Checking RGB: {rgb}")
                
                # Kırmızı tonları (Ürün Adı) - FFFF0000 formatını kontrol et
                if 'FFFF0000' in rgb or 'FF0000' in rgb or 'CC0000' in rgb:
                    return 'RED'
                # Mavi tonları (Ürün Açıklaması) - özel mavi tonları
                elif 'FF0070C0' in rgb or '0070C0' in rgb or '0000FF' in rgb or '4472C4' in rgb:
                    return 'BLUE'  
                # Turuncu tonları (İndirimli Fiyat) - Önce daha spesifik kontroller
                elif ('FFFFC000' in rgb or 'FFF4B183' in rgb or 'F4B183' in rgb or 'FF7F00' in rgb or 'FFA500' in rgb or 
                      'FF8C00' in rgb or 'FFFF9900' in rgb or 'FF9900' in rgb):
                    return 'ORANGE'
                # Sarı tonları (Firma) - FFFFFF00 formatını kontrol et
                elif 'FFFFFF00' in rgb or 'FFFF00' in rgb or 'FFC000' in rgb:
                    return 'YELLOW'
                # Yeşil tonları (Liste Fiyatı) - FF00B050 formatını kontrol et
                elif 'FF00B050' in rgb or '00B050' in rgb or '00FF00' in rgb or '008000' in rgb:
                    return 'GREEN'
                    
            except Exception as e:
                logger.warning(f"RGB parsing error: {e}")
                
        # Theme color kontrolü (Excel'de theme color kullanıldığında)
        if hasattr(color, 'theme') and color.theme is not None:
            try:
                theme = color.theme
                logger.debug(f"Checking theme color: {theme}")
                
                # Excel theme color mappings
                if theme == 2:  # Theme color 2 genelde koyu kırmızı
                    return 'RED'
                elif theme == 4:  # Theme color 4 genelde mavi
                    return 'BLUE'  
                elif theme == 5:  # Theme color 5 genelde sarı/accent
                    return 'YELLOW'
                elif theme == 6:  # Theme color 6 genelde yeşil
                    return 'GREEN'
                elif theme == 9:  # Theme color 9 - özel durum: hem yeşil hem turuncu olabilir
                    return 'ORANGE'  # Varsayılan turuncu, ama yeşil de olabilir
                elif theme == 7:  # Theme color 7 genelde turuncu
                    return 'ORANGE'
                    
            except Exception as e:
                logger.warning(f"Theme color parsing error: {e}")
                
        # Index renk kontrolü
        if hasattr(color, 'index') and color.index:
            try:
                index = str(color.index)
                logger.debug(f"Checking color index: {index}")
                # Excel'in standart renk indeksleri
                if index in ['10', '3']:  # Kırmızı
                    return 'RED' 
                elif index in ['12', '5']:  # Mavi
                    return 'BLUE'
                elif index in ['13', '6']:  # Sarı
                    return 'YELLOW'
                elif index in ['11', '4']:  # Yeşil
                    return 'GREEN'
                elif index in ['46', '53']:  # Turuncu
                    return 'ORANGE'
                elif index == '9':  # Bu dosyada index 9 İNDİRİMLİ fiyat için kullanılıyor
                    return 'ORANGE'
            except Exception as e:
                logger.warning(f"Index parsing error: {e}")
                
        return 'NONE'
    
    @staticmethod
    def parse_colored_excel(file_content: bytes, company_name: str = "Unknown") -> List[Dict[str, Any]]:
        """Parse Excel file using color-based column detection"""
        try:
            # Load workbook with data_only=True to get formula results
            workbook = openpyxl.load_workbook(io.BytesIO(file_content), data_only=True)
            all_products = []
            
            logger.info(f"Processing Excel with {len(workbook.sheetnames)} sheets: {workbook.sheetnames}")
            
            for sheet_name in workbook.sheetnames:
                logger.info(f"Processing sheet: {sheet_name}")
                sheet = workbook[sheet_name]
                
                # Find header row by looking for colored cells
                header_row = ColorBasedExcelService._find_colored_header_row(sheet)
                if header_row == -1:
                    logger.warning(f"No header found in sheet {sheet_name}, trying to analyze first row as data")
                    # Header yoksa direkt 0. satırı data olarak kabul et ve renkleri analiz et
                    column_mapping = ColorBasedExcelService._analyze_data_row_colors(sheet, 0)
                    if all(val == -1 for val in column_mapping.values()):
                        logger.warning(f"No colored columns found in {sheet_name}, skipping")
                        continue
                    header_row = -1  # Data başlangıcı için -1 kullan
                else:
                    logger.info(f"Found colored header at row {header_row + 1}")
                    # Analyze header colors to map columns
                    column_mapping = ColorBasedExcelService._analyze_header_colors(sheet, header_row)
                
                logger.info(f"Column mapping: {column_mapping}")
                
                # Extract products from this sheet
                sheet_products = ColorBasedExcelService._extract_products_from_sheet(
                    sheet, header_row, column_mapping, company_name
                )
                
                logger.info(f"Extracted {len(sheet_products)} products from {sheet_name}")
                all_products.extend(sheet_products)
            
            logger.info(f"Total products extracted: {len(all_products)}")
            return all_products
            
        except Exception as e:
            logger.error(f"Error in color-based Excel parsing: {e}")
            raise HTTPException(status_code=400, detail=f"Renkli Excel dosyası işlenemedi: {str(e)}")
    
    @staticmethod
    def _find_colored_header_row(sheet) -> int:
        """Find the header row with colored cells"""
        max_search_rows = min(20, sheet.max_row)
        
        for row_idx in range(max_search_rows):
            colored_cells = 0
            non_empty_cells = 0
            meaningful_cells = 0
            
            for col_idx in range(min(10, sheet.max_column)):
                cell = sheet.cell(row=row_idx + 1, column=col_idx + 1)
                if cell.value and str(cell.value).strip():
                    cell_text = str(cell.value).strip().lower()
                    non_empty_cells += 1
                    
                    # Meaningful header words
                    if any(word in cell_text for word in ['ürün', 'ad', 'açık', 'marka', 'firma', 'fiyat', 'price', 'name']):
                        meaningful_cells += 1
                    
                    color_category = ColorBasedExcelService.detect_color_category(cell.fill)
                    logger.debug(f"Row {row_idx + 1}, Col {col_idx + 1}: '{cell_text}' -> {color_category}")
                    if color_category != 'NONE':
                        colored_cells += 1
            
            logger.debug(f"Row {row_idx + 1}: colored={colored_cells}, meaningful={meaningful_cells}, non_empty={non_empty_cells}")
            
            # Header satırında en az 2 renkli hücre ve 2 anlamlı hücre olmalı
            if colored_cells >= 2 and meaningful_cells >= 2:
                return row_idx
        
        # Fallback: Anlamlı kelimeler içeren satırı bul
        for row_idx in range(max_search_rows):
            meaningful_cells = 0
            for col_idx in range(min(10, sheet.max_column)):
                cell = sheet.cell(row=row_idx + 1, column=col_idx + 1)
                if cell.value:
                    cell_text = str(cell.value).strip().lower()
                    if any(word in cell_text for word in ['ürün', 'ad', 'açık', 'marka', 'firma', 'fiyat']):
                        meaningful_cells += 1
            
            if meaningful_cells >= 3:
                return row_idx
                
        return -1
    
    @staticmethod
    def detect_currency_from_header(cell_value: str) -> str:
        """Detect currency from header cell text"""
        if not cell_value:
            return 'TRY'
            
        text = str(cell_value).upper()
        
        # Dolar kontrolü
        if any(keyword in text for keyword in ['$', 'DOLAR', 'DOLLAR', 'USD']):
            return 'USD'
        # Euro kontrolü  
        elif any(keyword in text for keyword in ['€', 'EURO', 'EUR']):
            return 'EUR'
        # TL kontrolü
        elif any(keyword in text for keyword in ['₺', 'TL', 'TRY', 'TÜRK', 'LIRA']):
            return 'TRY'
        # Varsayılan TRY
        else:
            return 'TRY'

    @staticmethod
    def _analyze_header_colors(sheet, header_row: int) -> Dict[str, int]:
        """Analyze header colors and map to column purposes - ONLY COLOR-BASED"""
        column_mapping = {
            'product_name': -1,
            'description': -1, 
            'company': -1,
            'list_price': -1,
            'discounted_price': -1,
            'currency': 'TRY'  # Varsayılan döviz
        }
        
        for col_idx in range(min(15, sheet.max_column)):
            cell = sheet.cell(row=header_row + 1, column=col_idx + 1)
            if not cell.value:
                continue
                
            color_category = ColorBasedExcelService.detect_color_category(cell.fill)
            
            # SADECE renk kategorilerine göre kolon belirleme - text-based fallback YOK
            if color_category == 'RED':  # Kırmızı = Ürün Adı
                column_mapping['product_name'] = col_idx
            elif color_category == 'BLUE':  # Mavi = Ürün Açıklaması
                column_mapping['description'] = col_idx
            elif color_category == 'YELLOW':  # Sarı = Firma
                column_mapping['company'] = col_idx
            elif color_category == 'GREEN':  # Yeşil = Liste Fiyatı
                column_mapping['list_price'] = col_idx
                # Yeşil sütun bulunduğunda döviz algıla
                detected_currency = ColorBasedExcelService.detect_currency_from_header(cell.value)
                column_mapping['currency'] = detected_currency
                logger.info(f"Detected currency from header '{cell.value}': {detected_currency}")
            elif color_category == 'ORANGE':  # Turuncu = İndirimli Fiyat
                column_mapping['discounted_price'] = col_idx
            # Diğer renkler veya renksiz veriler ignore edilir
        
        return column_mapping
    
    @staticmethod
    def _analyze_data_row_colors(sheet, data_row: int) -> Dict[str, int]:
        """Analyze first data row colors when no header is found - ONLY COLOR-BASED"""
        column_mapping = {
            'product_name': -1,
            'description': -1, 
            'company': -1,
            'list_price': -1,
            'discounted_price': -1,
            'currency': 'TRY'  # Header yoksa varsayılan TRY
        }
        
        for col_idx in range(min(15, sheet.max_column)):
            cell = sheet.cell(row=data_row + 1, column=col_idx + 1)
            if not cell.value:
                continue
                
            color_category = ColorBasedExcelService.detect_color_category(cell.fill)
            
            # SADECE renk kategorilerine göre kolon belirleme - text-based fallback YOK
            if color_category == 'RED':  # Kırmızı = Ürün Adı
                column_mapping['product_name'] = col_idx
            elif color_category == 'BLUE':  # Mavi = Ürün Açıklaması  
                column_mapping['description'] = col_idx
            elif color_category == 'YELLOW':  # Sarı = Firma
                column_mapping['company'] = col_idx
            elif color_category == 'GREEN':  # Yeşil = Liste Fiyatı
                column_mapping['list_price'] = col_idx
                # Header yoksa varsayılan TRY (log için)
                logger.info(f"No header found, using default currency: TRY")
            elif color_category == 'ORANGE':  # Turuncu = İndirimli Fiyat
                column_mapping['discounted_price'] = col_idx
            # Diğer renkler veya renksiz veriler ignore edilir
        
        return column_mapping
    
    @staticmethod
    def _extract_products_from_sheet(sheet, header_row: int, column_mapping: Dict[str, int], company_name: str) -> List[Dict[str, Any]]:
        """Extract products from a sheet using column mapping"""
        import random
        products = []
        
        # Start row hesaplama: header varsa header_row + 1, yoksa 0
        start_row = 0 if header_row == -1 else header_row + 1
        
        # Start from the appropriate row
        for row_idx in range(start_row, sheet.max_row):
            try:
                # Extract data based on column mapping
                product_name = ""
                description = ""
                detected_company = company_name
                list_price = 0
                discounted_price = None
                
                # Ürün adı (Kırmızı) - SADECE kırmızı hücre kabul edilir
                if column_mapping['product_name'] >= 0:
                    name_cell = sheet.cell(row=row_idx + 1, column=column_mapping['product_name'] + 1)
                    if (name_cell.value and 
                        ColorBasedExcelService.detect_color_category(name_cell.fill) == 'RED'):
                        product_name = str(name_cell.value).strip()

                # Açıklama (Mavi) - SADECE mavi hücre kabul edilir
                if column_mapping['description'] >= 0:
                    desc_cell = sheet.cell(row=row_idx + 1, column=column_mapping['description'] + 1)
                    if (desc_cell.value and 
                        ColorBasedExcelService.detect_color_category(desc_cell.fill) == 'BLUE'):
                        description = str(desc_cell.value).strip()

                # Firma (Sarı) - SADECE sarı hücre kabul edilir
                if column_mapping['company'] >= 0:
                    company_cell = sheet.cell(row=row_idx + 1, column=column_mapping['company'] + 1)
                    if (company_cell.value and 
                        ColorBasedExcelService.detect_color_category(company_cell.fill) == 'YELLOW'):
                        company_value = str(company_cell.value).strip()
                        # Excel formülü değilse VE sayısal değer değilse kullan
                        if not company_value.startswith('='):
                            try:
                                # Sayısal değer mi kontrol et
                                float(company_value)
                                # Sayısal değerse varsayılan firma adını kullan
                                logger.warning(f"Skipping numeric company name: {company_value}")
                            except ValueError:
                                # Sayısal değer değilse kullan
                                detected_company = company_value

                # Liste Fiyatı (Yeşil) - SADECE yeşil hücre kabul edilir
                if column_mapping['list_price'] >= 0:
                    price_cell = sheet.cell(row=row_idx + 1, column=column_mapping['list_price'] + 1)
                    if (price_cell.value and 
                        ColorBasedExcelService.detect_color_category(price_cell.fill) == 'GREEN'):
                        try:
                            list_price = float(str(price_cell.value).replace(',', '.'))
                        except:
                            list_price = 0

                # İndirimli Fiyat (Turuncu) - SADECE turuncu hücre kabul edilir
                if column_mapping['discounted_price'] >= 0:
                    disc_price_cell = sheet.cell(row=row_idx + 1, column=column_mapping['discounted_price'] + 1)
                    if (disc_price_cell.value and 
                        ColorBasedExcelService.detect_color_category(disc_price_cell.fill) == 'ORANGE'):
                        try:
                            discounted_price = float(str(disc_price_cell.value).replace(',', '.'))
                        except:
                            discounted_price = None

                # Özel mantık: Turuncu var ama yeşil yoksa
                if discounted_price and discounted_price > 0 and list_price == 0:
                    # İndirimli fiyat üzerine %20-30 arası rastgele zam ekle
                    markup_percentage = random.uniform(20, 30)
                    list_price = discounted_price * (1 + markup_percentage / 100)
                    logger.info(f"Generated list price for {product_name}: {discounted_price} + {markup_percentage:.1f}% = {list_price:.2f}")

                # Geçerli ürün kontrolü - en az liste fiyatı olmalı
                if (product_name and len(product_name) > 3 and 
                    list_price > 0 and 
                    not any(skip_word in product_name.lower() for skip_word in ['no', 'resim', 'ürün adı', 'toplam'])):
                    
                    products.append({
                        'name': product_name,
                        'description': description if description else None,
                        'company_name': detected_company,
                        'list_price': list_price,
                        'discounted_price': discounted_price if discounted_price and discounted_price > 0 else None,
                        'currency': column_mapping.get('currency', 'TRY')  # Algılanan dövizi kullan
                    })
                    
            except Exception as e:
                logger.warning(f"Error processing row {row_idx + 1}: {e}")
                continue
        
        return products

# Excel parsing service
class ExcelService:
    @staticmethod
    def parse_excel_file(file_content: bytes) -> List[Dict[str, Any]]:
        """Parse Excel file and extract product data"""
        try:
            # Read Excel file
            df = pd.read_excel(io.BytesIO(file_content))
            
            logger.info(f"Excel file loaded: {len(df)} rows, {len(df.columns)} columns")
            
            # İlk veri satırını bul (header'ı tespit et)
            header_row = ExcelService._find_header_row(df)
            logger.info(f"Header row found at index: {header_row}")
            
            if header_row == -1:
                # Header bulunamazsa tüm kolonları kontrol et
                products = ExcelService._parse_without_header(df)
            else:
                # Header bulunduysa o satırdan itibaren parse et
                products = ExcelService._parse_with_header(df, header_row)
            
            logger.info(f"Total products extracted: {len(products)}")
            return products
            
        except Exception as e:
            logger.error(f"Error parsing Excel file: {e}")
            raise HTTPException(status_code=400, detail=f"Excel dosyası işlenemedi: {str(e)}")
    
    @staticmethod
    def _find_header_row(df) -> int:
        """Excel dosyasında header satırını bul"""
        # Aranacak header kelimeleri
        header_keywords = [
            # Ürün adı varyantları
            'ürün', 'urun', 'product', 'malzeme', 'güneş', 'panel', 'solar', 'akü', 'batarya',
            'inverter', 'regülatör', 'kablo', 'malzemeler', 'items',
            # Fiyat varyantları  
            'fiyat', 'price', 'liste', 'list', 'tutar', 'amount', 'maliyet', 'cost',
            # İndirim varyantları
            'indirim', 'iskonto', 'discount', 'net', 'indirimli',
            # Para birimi varyantları
            'para', 'currency', 'birim', 'döviz', 'tl', 'usd', 'eur', '$', '€', '₺'
        ]
        
        for row_idx in range(min(20, len(df))):  # İlk 20 satırı kontrol et
            row_text = ""
            for col_idx in range(len(df.columns)):
                cell_value = df.iloc[row_idx, col_idx]
                if pd.notna(cell_value):
                    row_text += str(cell_value).lower() + " "
            
            # Bu satırda header keyword'leri var mı?
            keyword_count = sum(1 for keyword in header_keywords if keyword in row_text)
            if keyword_count >= 2:  # En az 2 keyword varsa header olabilir
                logger.info(f"Header row candidate at {row_idx}: '{row_text[:100]}...'")
                return row_idx
        
        return -1
    
    @staticmethod
    def _parse_with_header(df, header_row: int) -> List[Dict[str, Any]]:
        """Header'lı Excel dosyasını parse et"""
        # Header satırını kullanarak kolonları yeniden adlandır
        df_data = df.iloc[header_row:].copy()
        df_data.columns = df.iloc[header_row]
        df_data = df_data.iloc[1:]  # Header satırını atla
        
        return ExcelService._extract_products_from_dataframe(df_data)
    
    @staticmethod
    def _parse_without_header(df) -> List[Dict[str, Any]]:
        """Header'sız Excel dosyasını parse et"""
        logger.info("Parsing without header, analyzing all columns...")
        
        products = []
        
        # Her satırı kontrol et, veri olan satırları bul
        for row_idx in range(len(df)):
            row_data = {}
            product_name = ""
            list_price = 0
            discounted_price = None
            currency = "USD"  # Default currency
            
            # Bu satırdaki tüm hücreleri kontrol et
            for col_idx in range(len(df.columns)):
                cell_value = df.iloc[row_idx, col_idx]
                
                if pd.notna(cell_value):
                    str_value = str(cell_value).strip()
                    
                    # Fiyat hücresi mi kontrol et (sayısal değer)
                    try:
                        numeric_value = float(str_value.replace(',', '.'))
                        if 1 <= numeric_value <= 100000:  # Makul fiyat aralığı
                            if list_price == 0:
                                list_price = numeric_value
                            elif discounted_price is None and numeric_value < list_price:
                                discounted_price = numeric_value
                    except:
                        pass
                    
                    # Ürün adı hücresi mi kontrol et (text ve uzun)
                    if len(str_value) > 10 and any(char.isalpha() for char in str_value):
                        if not product_name or len(str_value) > len(product_name):
                            product_name = str_value
                    
                    # Para birimi kontrol et
                    if any(curr in str_value.upper() for curr in ['USD', 'EUR', 'TRY', '$', '€', '₺']):
                        if 'USD' in str_value.upper() or '$' in str_value:
                            currency = 'USD'
                        elif 'EUR' in str_value.upper() or '€' in str_value:
                            currency = 'EUR'
                        elif 'TRY' in str_value.upper() or '₺' in str_value:
                            currency = 'TRY'
            
            # Geçerli ürün bilgisi var mı kontrol et
            if product_name and list_price > 0:
                products.append({
                    'name': product_name,
                    'list_price': list_price,
                    'currency': currency,
                    'discounted_price': discounted_price
                })
                logger.info(f"Extracted product: {product_name[:50]}... - ${list_price}")
        
        return products
    
    @staticmethod
    def _extract_products_from_dataframe(df) -> List[Dict[str, Any]]:
        """DataFrame'den ürün verilerini çıkar"""
        products = []
        
        # ELEKTROZİRVE formatını kontrol et (basit 4 kolon)
        if len(df.columns) == 4:
            logger.info("Detected ELEKTROZİRVE format (4 columns)")
            return ExcelService._parse_elektrozirve_format(df)
        
        # HAVENSİS formatını kontrol et (karmaşık multi-column)
        elif len(df.columns) > 10:
            logger.info("Detected HAVENSİS format (multi-column)")
            return ExcelService._parse_havensis_format(df)
        
        # Genel format parsing
        else:
            logger.info("Using general format parsing")
            return ExcelService._parse_general_format(df)
    
    @staticmethod
    def _parse_elektrozirve_format(df) -> List[Dict[str, Any]]:
        """ELEKTROZİRVE formatında Excel parse et"""
        products = []
        
        # İlk satır header (Güneş Panelleri, LİSTE FİYATI, İskonto, Net Fiyat)
        df.columns = ['product_name', 'list_price', 'discount_rate', 'net_price']
        
        for index, row in df.iterrows():
            try:
                if index == 0:  # Header satırını atla
                    continue
                
                product_name = str(row['product_name']).strip() if pd.notna(row['product_name']) else ""
                list_price = float(row['list_price']) if pd.notna(row['list_price']) else 0
                net_price = float(row['net_price']) if pd.notna(row['net_price']) else 0
                
                # Kategori başlıkları atla (örn: "Esnek Güneş Panelleri")
                if ('panelleri' in product_name.lower() or 'aküler' in product_name.lower() or 
                    'regülatörler' in product_name.lower()) and list_price == 0:
                    continue
                
                # Geçerli ürün kontrolü
                if (product_name and len(product_name) > 5 and 
                    list_price > 0 and not product_name.lower().startswith('liste')):
                    
                    products.append({
                        'name': product_name,
                        'list_price': list_price,
                        'currency': 'TRY',  # ELEKTROZİRVE TL fiyatları
                        'discounted_price': net_price if net_price != list_price else None
                    })
                    logger.info(f"Added ELEKTROZİRVE product: {product_name[:50]}... - {list_price} TL")
                    
            except Exception as e:
                logger.warning(f"Error processing ELEKTROZİRVE row {index}: {e}")
                continue
        
        return products
    
    @staticmethod
    def _parse_havensis_format(df) -> List[Dict[str, Any]]:
        """HAVENSİS formatında Excel parse et"""
        products = []
        
        # HAVENSİS formatı: Col3=Ürün, Col6=Fiyat$, Col7=İskonto, Col8=İskontolu Fiyat$
        product_col = 3
        price_col = 6
        discount_rate_col = 7
        discounted_price_col = 8
        
        for index, row in df.iterrows():
            try:
                if index < 12:  # İlk 12 satır header/boş satırlar
                    continue
                
                # Ürün adı (Col3)
                product_name = ""
                if len(row) > product_col and pd.notna(row.iloc[product_col]):
                    product_name = str(row.iloc[product_col]).strip()
                
                # Liste fiyatı (Col6)
                list_price = 0
                if len(row) > price_col and pd.notna(row.iloc[price_col]):
                    try:
                        list_price = float(row.iloc[price_col])
                    except:
                        list_price = 0
                
                # İndirimli fiyat (Col8)
                discounted_price = None
                if len(row) > discounted_price_col and pd.notna(row.iloc[discounted_price_col]):
                    try:
                        discounted_price = float(row.iloc[discounted_price_col])
                    except:
                        discounted_price = None
                
                # Geçerli ürün kontrolü
                if (product_name and len(product_name) > 10 and 
                    list_price > 0 and 'panel' in product_name.lower()):
                    
                    products.append({
                        'name': product_name,
                        'list_price': list_price,
                        'currency': 'USD',  # HAVENSİS USD fiyatları
                        'discounted_price': discounted_price
                    })
                    logger.info(f"Added HAVENSİS product: {product_name[:50]}... - ${list_price}")
                    
            except Exception as e:
                logger.warning(f"Error processing HAVENSİS row {index}: {e}")
                continue
        
        return products
    
    @staticmethod
    def _parse_general_format(df) -> List[Dict[str, Any]]:
        """Genel format parsing"""
        products = []
        
        # Gelişmiş kolon mapping
        column_mapping = {
            # Ürün adı varyantları
            'ürün adı': 'product_name', 'urun adi': 'product_name', 'product name': 'product_name',
            'ürün': 'product_name', 'urun': 'product_name', 'product': 'product_name',
            'malzeme': 'product_name', 'malzemeler': 'product_name', 'item': 'product_name',
            'güneş panelleri': 'product_name', 'gunes panelleri': 'product_name',
            'solar panel': 'product_name', 'panel': 'product_name',
            'aküler': 'product_name', 'akü': 'product_name', 'batarya': 'product_name',
            'ad': 'product_name', 'name': 'product_name',
            
            # Liste fiyatı varyantları
            'liste fiyatı': 'list_price', 'liste fiyati': 'list_price', 'list price': 'list_price',
            'fiyat$': 'list_price', 'fiyat $': 'list_price', 'fiyat': 'list_price',
            'liste': 'list_price', 'list': 'list_price', 'price': 'list_price',
            'tutar': 'list_price', 'amount': 'list_price', 'maliyet': 'list_price',
            
            # İndirimli fiyat varyantları
            'indirimli fiyat $': 'discounted_price', 'indirimli fiyat$': 'discounted_price',
            'iskontolu fiyat $': 'discounted_price', 'iskontolu fiyat$': 'discounted_price',
            'indirimli fiyat': 'discounted_price', 'indirimli fiyati': 'discounted_price',
            'iskontolu fiyat': 'discounted_price', 'iskontolu fiyati': 'discounted_price',
            'net fiyat': 'discounted_price', 'net price': 'discounted_price',
            'discounted price': 'discounted_price', 'discount price': 'discounted_price',
            'net': 'discounted_price', 'indirim': 'discounted_price', 'iskonto': 'discounted_price',
            
            # Para birimi varyantları
            'para birimi': 'currency', 'currency': 'currency', 'birim': 'currency',
            'döviz': 'currency', 'doviz': 'currency'
        }
        
        # Kolonları normalize et
        df.columns = df.columns.astype(str).str.lower().str.strip()
        logger.info(f"Normalized columns: {list(df.columns)}")
        
        # Kolon mapping uygula
        for col in df.columns:
            for mapping_key, mapping_value in column_mapping.items():
                if mapping_key in col:
                    df = df.rename(columns={col: mapping_value})
                    logger.info(f"Mapped column '{col}' to '{mapping_value}'")
                    break
        
        logger.info(f"Final mapped columns: {list(df.columns)}")
        
        # Eğer standart kolonlar yoksa, konum bazlı mapping dene
        if 'product_name' not in df.columns:
            # İlk metin kolonu ürün adı olabilir
            for col in df.columns:
                if df[col].dtype == 'object':
                    df = df.rename(columns={col: 'product_name'})
                    logger.info(f"Using first text column '{col}' as product_name")
                    break
        
        if 'list_price' not in df.columns:
            # İlk sayısal kolon liste fiyatı olabilir  
            for col in df.columns:
                if col != 'product_name' and pd.api.types.is_numeric_dtype(df[col]):
                    df = df.rename(columns={col: 'list_price'})
                    logger.info(f"Using first numeric column '{col}' as list_price")
                    break
        
        # Ürünleri çıkar
        for index, row in df.iterrows():
            try:
                # Ürün adı
                product_name = ""
                if 'product_name' in row:
                    product_name = str(row['product_name']).strip() if pd.notna(row['product_name']) else ""
                
                # Liste fiyatı
                list_price = 0
                if 'list_price' in row:
                    try:
                        list_price = float(row['list_price']) if pd.notna(row['list_price']) else 0
                    except:
                        list_price = 0
                
                # İndirimli fiyat
                discounted_price = None
                if 'discounted_price' in row and pd.notna(row['discounted_price']):
                    try:
                        discounted_price = float(row['discounted_price'])
                    except:
                        discounted_price = None
                
                # Para birimi - varsayılan USD
                currency = "USD"
                if 'currency' in row and pd.notna(row['currency']):
                    currency = str(row['currency']).strip().upper()
                
                # USD işareti olan fiyatları tespit et
                for col_name, col_value in row.items():
                    if pd.notna(col_value) and '$' in str(col_value):
                        currency = 'USD'
                        break
                
                # Geçerli ürün kontrolü
                if product_name and len(product_name) > 3 and list_price > 0:
                    product = {
                        'name': product_name,
                        'list_price': list_price,
                        'currency': currency,
                        'discounted_price': discounted_price
                    }
                    products.append(product)
                    logger.info(f"Added product: {product_name[:50]}... - {list_price} {currency}")
                else:
                    logger.info(f"Skipped row {index}: name='{product_name}', price={list_price}")
                    
            except Exception as e:
                logger.warning(f"Error processing row {index}: {e}")
                continue
        
        return products

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

class ProductUpdate(BaseModel):
    name: Optional[str] = None
    description: Optional[str] = None
    image_url: Optional[str] = None
    list_price: Optional[Decimal] = None
    discounted_price: Optional[Decimal] = None
    currency: Optional[str] = None
    category_id: Optional[str] = None

@api_router.patch("/products/{product_id}")
async def update_product(product_id: str, update_data: ProductUpdate):
    """Update a product"""
    try:
        # Get existing product
        existing_product = await db.products.find_one({"id": product_id})
        if not existing_product:
            raise HTTPException(status_code=404, detail="Ürün bulunamadı")
        
        # Prepare update data
        update_dict = {}
        if update_data.name is not None:
            update_dict["name"] = update_data.name
        if update_data.description is not None:
            update_dict["description"] = update_data.description
        if update_data.image_url is not None:
            update_dict["image_url"] = update_data.image_url
        if update_data.list_price is not None:
            update_dict["list_price"] = float(update_data.list_price)
        if update_data.discounted_price is not None:
            update_dict["discounted_price"] = float(update_data.discounted_price)
        if update_data.currency is not None:
            update_dict["currency"] = update_data.currency.upper()
        if update_data.category_id is not None:
            update_dict["category_id"] = update_data.category_id
        
        # If currency or prices changed, recalculate TRY prices
        if update_data.currency is not None or update_data.list_price is not None or update_data.discounted_price is not None:
            currency = update_data.currency.upper() if update_data.currency else existing_product["currency"]
            list_price = float(update_data.list_price) if update_data.list_price is not None else existing_product["list_price"]
            discounted_price = float(update_data.discounted_price) if update_data.discounted_price is not None else existing_product.get("discounted_price")
            
            # Convert to TRY
            try:
                list_price_try = await currency_service.convert_to_try(Decimal(str(list_price)), currency)
                update_dict["list_price_try"] = float(list_price_try)
            except Exception as e:
                logger.warning(f"Failed to convert list price to TRY: {e}")
                update_dict["list_price_try"] = float(list_price)
            
            if discounted_price is not None:
                try:
                    discounted_price_try = await currency_service.convert_to_try(Decimal(str(discounted_price)), currency)
                    update_dict["discounted_price_try"] = float(discounted_price_try)
                except Exception as e:
                    logger.warning(f"Failed to convert discounted price to TRY: {e}")
                    update_dict["discounted_price_try"] = float(discounted_price)
            else:
                update_dict["discounted_price_try"] = None
        
        # Update product
        if update_dict:
            result = await db.products.update_one(
                {"id": product_id},
                {"$set": update_dict}
            )
            
            if result.modified_count == 0:
                raise HTTPException(status_code=404, detail="Ürün güncellenemedi")
        
        # Get updated product
        updated_product = await db.products.find_one({"id": product_id})
        return {
            "success": True,
            "message": "Ürün başarıyla güncellendi",
            "product": Product(**updated_product)
        }
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error updating product: {e}")
        raise HTTPException(status_code=500, detail="Ürün güncellenemedi")

@api_router.delete("/products/{product_id}")
async def delete_product(product_id: str):
    """Delete a product"""
    try:
        result = await db.products.delete_one({"id": product_id})
        if result.deleted_count == 0:
            raise HTTPException(status_code=404, detail="Ürün bulunamadı")
        
        return {"success": True, "message": "Ürün silindi"}
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error deleting product: {e}")
        raise HTTPException(status_code=500, detail="Ürün silinemedi")

# ===== QUOTE ENDPOINTS =====

@api_router.post("/quotes", response_model=QuoteResponse)
async def create_quote(quote: QuoteCreate):
    """Create a new quote"""
    try:
        # Validate products exist
        product_ids = [p["id"] for p in quote.products]
        products_cursor = db.products.find({"id": {"$in": product_ids}})
        products = await products_cursor.to_list(length=None)
        
        if len(products) != len(quote.products):
            raise HTTPException(status_code=400, detail="Some products not found")
        
        # Create product-quantity mapping
        product_quantities = {p["id"]: p.get("quantity", 1) for p in quote.products}
        
        # Calculate totals
        total_list_price = 0
        total_discounted_price = 0
        processed_products = []
        
        for product in products:
            # Get company info
            company = await db.companies.find_one({"id": product["company_id"]})
            
            # Get quantity for this product
            quantity = product_quantities.get(product["id"], 1)
            
            list_price_try = float(product.get("list_price_try", 0))
            discounted_price_try = float(product.get("discounted_price_try", 0)) if product.get("discounted_price_try") else list_price_try
            
            # Calculate totals with quantity
            total_list_price += list_price_try * quantity
            total_discounted_price += discounted_price_try * quantity
            
            processed_products.append({
                "id": product["id"],
                "name": product["name"],
                "description": product.get("description"),
                "company_name": company["name"] if company else "Unknown",
                "list_price": product["list_price"],
                "list_price_try": list_price_try,
                "discounted_price": product.get("discounted_price"),
                "discounted_price_try": discounted_price_try,
                "currency": product["currency"],
                "quantity": quantity
            })
        
        # Apply quote discount
        quote_discount_amount = total_discounted_price * (quote.discount_percentage / 100)
        total_net_price = total_discounted_price - quote_discount_amount
        
        # Create quote document
        quote_doc = {
            "id": str(uuid.uuid4()),
            "name": quote.name,
            "customer_name": quote.customer_name,
            "customer_email": quote.customer_email,
            "discount_percentage": quote.discount_percentage,
            "total_list_price": total_list_price,
            "total_discounted_price": total_discounted_price,
            "total_net_price": total_net_price,
            "products": processed_products,
            "notes": quote.notes,
            "created_at": datetime.utcnow().isoformat() + "Z",
            "status": "active"
        }
        
        result = await db.quotes.insert_one(quote_doc)
        
        logger.info(f"Quote created: {quote.name} with {len(products)} products")
        return quote_doc
        
    except Exception as e:
        logger.error(f"Error creating quote: {e}")
        raise HTTPException(status_code=500, detail=f"Error creating quote: {str(e)}")

@api_router.get("/quotes", response_model=List[QuoteResponse])
async def get_quotes():
    """Get all quotes"""
    try:
        quotes_cursor = db.quotes.find({"status": "active"}).sort("created_at", -1)
        quotes = await quotes_cursor.to_list(length=None)
        
        return quotes
        
    except Exception as e:
        logger.error(f"Error fetching quotes: {e}")
        raise HTTPException(status_code=500, detail=f"Error fetching quotes: {str(e)}")

@api_router.get("/quotes/{quote_id}", response_model=QuoteResponse)
async def get_quote(quote_id: str):
    """Get specific quote by ID"""
    try:
        quote = await db.quotes.find_one({"id": quote_id})
        
        if not quote:
            raise HTTPException(status_code=404, detail="Quote not found")
        
        return quote
        
    except Exception as e:
        logger.error(f"Error fetching quote: {e}")
        raise HTTPException(status_code=500, detail=f"Error fetching quote: {str(e)}")

@api_router.delete("/quotes/{quote_id}")
async def delete_quote(quote_id: str):
    """Delete a quote"""
    try:
        result = await db.quotes.update_one(
            {"id": quote_id},
            {"$set": {"status": "deleted"}}
        )
        
        if result.matched_count == 0:
            raise HTTPException(status_code=404, detail="Quote not found")
        
        return {"success": True, "message": "Quote deleted successfully"}
        
    except Exception as e:
        logger.error(f"Error deleting quote: {e}")
        raise HTTPException(status_code=500, detail=f"Error deleting quote: {str(e)}")

class PDFQuoteGenerator:
    def __init__(self):
        self.setup_fonts()
        self.styles = getSampleStyleSheet()
        self.setup_styles()
    
    def setup_fonts(self):
        """Montserrat fontlarını kaydet"""
        try:
            font_dir = Path(__file__).parent / 'fonts'
            
            # Montserrat Regular font
            montserrat_regular_path = font_dir / 'Montserrat-Regular.ttf'
            if montserrat_regular_path.exists():
                pdfmetrics.registerFont(TTFont('Montserrat', str(montserrat_regular_path)))
                logger.info("Montserrat Regular font loaded successfully")
            else:
                logger.warning("Montserrat Regular font not found, using Helvetica")
            
            # Montserrat Bold font
            montserrat_bold_path = font_dir / 'Montserrat-Bold.ttf'
            if montserrat_bold_path.exists():
                pdfmetrics.registerFont(TTFont('Montserrat-Bold', str(montserrat_bold_path)))
                logger.info("Montserrat Bold font loaded successfully")
            else:
                logger.warning("Montserrat Bold font not found, using Helvetica-Bold")
                
        except Exception as e:
            logger.error(f"Font loading error: {e}")
            # Fallback to default fonts
            pass
    
    def setup_styles(self):
        """PDF için özel stiller tanımla - Türkçe karakter desteği ile"""
        
        # Ana renk paleti - #25c7eb temalı
        primary_color = colors.HexColor('#25c7eb')  # Ana turkuaz
        secondary_color = colors.HexColor('#1ba3cc')  # Koyu turkuaz
        accent_color = colors.HexColor('#85e8ff')    # Açık turkuaz
        text_color = colors.HexColor('#2d3748')      # Koyu gri
        
        # Başlık stili
        self.title_style = ParagraphStyle(
            'CustomTitle',
            parent=self.styles['Heading1'],
            fontName='Montserrat-Bold',
            fontSize=22,
            spaceAfter=25,
            spaceBefore=10,
            alignment=TA_CENTER,
            textColor=primary_color,
            leading=26
        )
        
        # Alt başlık stili
        self.subtitle_style = ParagraphStyle(
            'SubTitle',
            parent=self.styles['Heading2'],
            fontName='Montserrat',
            fontSize=14,
            spaceAfter=15,
            spaceBefore=10,
            alignment=TA_LEFT,
            textColor=secondary_color,
            leading=18
        )
        
        # Firma bilgi stili
        self.company_style = ParagraphStyle(
            'CompanyInfo',
            parent=self.styles['Normal'],
            fontName='Montserrat',
            fontSize=11,
            spaceAfter=6,
            alignment=TA_LEFT,
            textColor=text_color,
            leading=14
        )
        
        # Normal metin stili
        self.normal_style = ParagraphStyle(
            'CustomNormal',
            parent=self.styles['Normal'],
            fontName='Montserrat',
            fontSize=10,
            spaceAfter=8,
            textColor=text_color,
            leading=13
        )
        
        # Veri stili (tablolar için)
        self.data_style = ParagraphStyle(
            'DataText',
            parent=self.styles['Normal'],
            fontName='Montserrat',
            fontSize=9,
            spaceAfter=4,
            textColor=text_color,
            leading=12
        )
        
        # Footer stili
        self.footer_style = ParagraphStyle(
            'Footer',
            parent=self.styles['Normal'],
            fontName='Montserrat',
            fontSize=9,
            alignment=TA_LEFT,
            textColor=colors.HexColor('#718096'),
            spaceAfter=6,
            leading=11
        )
        
        # Fiyat vurgu stili
        self.price_style = ParagraphStyle(
            'PriceHighlight',
            parent=self.styles['Normal'],
            fontName='Montserrat-Bold',
            fontSize=16,
            alignment=TA_RIGHT,
            textColor=primary_color,
            spaceAfter=10,
            leading=20
        )

    def create_quote_pdf(self, quote_data: Dict) -> BytesIO:
        """Gelişmiş teklif PDF'i oluştur - Türkçe karakter desteği ile"""
        buffer = BytesIO()
        
        # Yüksek kaliteli PDF ayarları
        doc = SimpleDocTemplate(
            buffer,
            pagesize=A4,
            rightMargin=2.5*cm,
            leftMargin=2.5*cm,
            topMargin=2*cm,
            bottomMargin=2*cm,
            title=f"Teklif - {quote_data.get('name', 'Adsız')}",
            author="Karavan Elektrik Ekipmanları"
        )
        
        story = []
        
        # Üst header bölümü
        story.append(self._create_modern_header())
        story.append(Spacer(1, 25))
        
        # Teklif başlığı
        quote_name = quote_data.get('name', 'Fiyat Teklifi')
        story.append(Paragraph(f"<b>{quote_name}</b>", self.title_style))
        story.append(Spacer(1, 15))
        
        # Teklif bilgileri satırı (Tarih, Geçerlilik vs.)
        story.append(self._create_quote_info_section(quote_data))
        story.append(Spacer(1, 25))
        
        # Ürün tablosu başlığı
        story.append(Paragraph("<b>Teklif Detayları</b>", self.subtitle_style))
        story.append(Spacer(1, 10))
        
        # Ürün tablosu
        story.append(self._create_modern_products_table(quote_data['products']))
        story.append(Spacer(1, 25))
        
        # Toplam hesaplama bölümü
        story.extend(self._create_modern_totals_section(quote_data))
        story.append(Spacer(1, 30))
        
        # Footer notları
        story.extend(self._create_modern_footer())
        
        # PDF oluştur
        doc.build(story)
        buffer.seek(0)
        return buffer
    
    def _create_modern_header(self):
        """Modern firma bilgileri başlığı"""
        primary_color = colors.HexColor('#25c7eb')
        
        company_info = [
            "<b><font size='16' color='#25c7eb'>KARAVAN ELEKTRİK EKİPMANLARI</font></b>",
            "<font size='11' color='#1ba3cc'><b>Güneş Enerjisi Sistemleri ve Ekipmanları</b></font>",
            " ",
            "<font size='10'>Adres: Hatip, Sarı Salkım 3.Sokak Mobilyacılar Sitesi No: B1, 59000 Çorlu/Tekirdağ</font>",
            "<font size='10'>Telefon: 0505 813 77 65</font>",
            "<font size='10'>E-posta: info@karavan-elektrik.com</font>"
        ]
        
        header_text = "<br/>".join(company_info)
        return Paragraph(header_text, self.company_style)
    
    def _create_quote_info_section(self, quote_data: Dict):
        """Teklif bilgileri bölümü (tarih, geçerlilik vs.)"""
        try:
            created_date = datetime.fromisoformat(quote_data['created_at'].replace('Z', '+00:00'))
            date_str = created_date.strftime('%d.%m.%Y')
        except:
            date_str = datetime.now().strftime('%d.%m.%Y')
        
        # Bilgi tablosu oluştur
        info_data = [
            [
                Paragraph("<b>Başlangıç Tarihi:</b>", self.normal_style),
                Paragraph(date_str, self.normal_style),
                Paragraph("<b>Bitiş Tarihi:</b>", self.normal_style),
                Paragraph(date_str, self.normal_style)
            ]
        ]
        
        info_table = Table(info_data, colWidths=[4*cm, 3*cm, 4*cm, 3*cm])
        info_table.setStyle(TableStyle([
            ('BACKGROUND', (0, 0), (-1, -1), colors.HexColor('#f7fafc')),
            ('ALIGN', (0, 0), (-1, -1), 'LEFT'),
            ('FONTNAME', (0, 0), (-1, -1), 'Montserrat'),
            ('FONTSIZE', (0, 0), (-1, -1), 10),
            ('GRID', (0, 0), (-1, -1), 0.5, colors.HexColor('#e2e8f0')),
            ('VALIGN', (0, 0), (-1, -1), 'MIDDLE'),
            ('TOPPADDING', (0, 0), (-1, -1), 8),
            ('BOTTOMPADDING', (0, 0), (-1, -1), 8),
        ]))
        
        return info_table
    
    def _create_modern_products_table(self, products: List[Dict]):
        """Modern tasarımda ürün tablosu oluştur"""
        primary_color = colors.HexColor('#25c7eb')
        secondary_color = colors.HexColor('#1ba3cc')
        accent_color = colors.HexColor('#f0f9ff')
        
        # Tablo başlıkları
        headers = [
            Paragraph("<b>Ürün Adı</b>", self.data_style),
            Paragraph("<b>Marka</b>", self.data_style), 
            Paragraph("<b>Miktar</b>", self.data_style),
            Paragraph("<b>Birim Fiyat</b>", self.data_style),
            Paragraph("<b>Toplam Fiyat</b>", self.data_style)
        ]
        
        data = [headers]
        
        # Ürün satırları
        for product in products:
            quantity = product.get('quantity', 1)
            unit_price = product.get('discounted_price_try', product.get('list_price_try', 0))
            total_price = unit_price * quantity
            
            row = [
                Paragraph(product.get('name', ''), self.data_style),
                Paragraph(product.get('company_name', ''), self.data_style),
                Paragraph(str(quantity), self.data_style),
                Paragraph(f"₺ {self._format_price_modern(unit_price)}", self.data_style),
                Paragraph(f"<b>₺ {self._format_price_modern(total_price)}</b>", self.data_style)
            ]
            data.append(row)
        
        # Tablo oluştur
        table = Table(data, colWidths=[6*cm, 3*cm, 2*cm, 3*cm, 3*cm])
        table.setStyle(TableStyle([
            # Başlık stili
            ('BACKGROUND', (0, 0), (-1, 0), primary_color),
            ('TEXTCOLOR', (0, 0), (-1, 0), colors.white),
            ('ALIGN', (0, 0), (-1, 0), 'CENTER'),
            ('FONTNAME', (0, 0), (-1, 0), 'Montserrat-Bold'),
            ('FONTSIZE', (0, 0), (-1, 0), 10),
            ('TOPPADDING', (0, 0), (-1, 0), 12),
            ('BOTTOMPADDING', (0, 0), (-1, 0), 12),
            
            # Veri satırları - Alternatif renklendirme
            ('BACKGROUND', (0, 1), (-1, -1), accent_color),
            ('ROWBACKGROUNDS', (0, 1), (-1, -1), [colors.white, accent_color]),
            ('ALIGN', (2, 1), (2, -1), 'CENTER'),  # Miktar ortala
            ('ALIGN', (3, 1), (-1, -1), 'RIGHT'),  # Fiyatları sağa hizala
            ('FONTNAME', (0, 1), (-1, -1), 'Montserrat'),
            ('FONTSIZE', (0, 1), (-1, -1), 9),
            ('TOPPADDING', (0, 1), (-1, -1), 8),
            ('BOTTOMPADDING', (0, 1), (-1, -1), 8),
            
            # Çerçeve
            ('GRID', (0, 0), (-1, -1), 0.5, colors.HexColor('#cbd5e0')),
            ('VALIGN', (0, 0), (-1, -1), 'MIDDLE'),
            
            # Son satır vurgusu (toplam fiyatlar için)
            ('FONTNAME', (4, 1), (4, -1), 'Montserrat-Bold'),
            ('TEXTCOLOR', (4, 1), (4, -1), secondary_color),
        ]))
        
        return table
    
    def _create_modern_totals_section(self, quote_data: Dict):
        """Modern toplam hesaplama bölümü"""
        primary_color = colors.HexColor('#25c7eb')
        secondary_color = colors.HexColor('#1ba3cc')
        
        totals_content = []
        
        # Ara toplam
        subtotal_text = f"Ara Toplam: <b>₺ {self._format_price_modern(quote_data.get('total_discounted_price', 0))}</b>"
        totals_content.append(Paragraph(subtotal_text, self.normal_style))
        
        # İndirim (eğer varsa)  
        discount_percentage = quote_data.get('discount_percentage', 0)
        if discount_percentage > 0:
            discount_amount = quote_data.get('total_discounted_price', 0) - quote_data.get('total_net_price', 0)
            discount_text = f"İndirim (%{discount_percentage}): <font color='#dc2626'>-₺ {self._format_price_modern(discount_amount)}</font>"
            totals_content.append(Paragraph(discount_text, self.normal_style))
            totals_content.append(Spacer(1, 8))
        
        # Net toplam - büyük ve vurgulanmış
        net_total = quote_data.get('total_net_price', 0)
        net_total_text = f"<font size='18' color='{primary_color}'><b>NET TOPLAM: ₺ {self._format_price_modern(net_total)}</b></font>"
        totals_content.append(Paragraph(net_total_text, self.price_style))
        
        return totals_content
    
    def _create_modern_footer(self):
        """Modern footer mesajı"""
        footer_content = []
        
        # Önemli notlar başlığı
        footer_content.append(Paragraph("<b><font color='#1ba3cc'>ÖNEMLİ NOTLAR:</font></b>", self.subtitle_style))
        footer_content.append(Spacer(1, 8))
        
        # Notlar listesi
        notes = [
            "• Yukarıdaki fiyatlandırmanın, 1 hafta geçerli olduğunu lütfen göz önünde bulundurunuz.",
            "• Fiyatlara KDV dahildir.",
            "• Ürün özellikleri ve fiyatları değişiklik gösterebilir.",
            "• Montaj ve nakliye masrafları ayrıca hesaplanacaktır.",
            "• Teknik destek ve garanti şartları ayrıca belirtilecektir."
        ]
        
        notes_text = "<br/>".join(notes)
        footer_content.append(Paragraph(notes_text, self.footer_style))
        
        return footer_content
    
    def _format_price_modern(self, price):
        """Modern Türkçe fiyat formatla"""
        try:
            if price is None:
                return "0,00"
            
            price_float = float(price)
            if price_float == 0:
                return "0,00"
                
            # Türkçe format: nokta binlik ayırıcı, virgül ondalık ayırıcı
            formatted = f"{price_float:,.2f}"
            # Binlik ayırıcıyı nokta, ondalık ayırıcıyı virgül yap
            formatted = formatted.replace(',', 'TEMP').replace('.', ',').replace('TEMP', '.')
            return formatted
        except (ValueError, TypeError):
            return "0,00"
    
    def _format_price(self, price):
        """Eski format - geriye uyumluluk için"""
        return self._format_price_modern(price)

# ===== PDF QUOTE ENDPOINT =====

@app.get("/api/quotes/{quote_id}/pdf")
async def download_quote_pdf(quote_id: str):
    """Teklif PDF'ini indir"""
    try:
        db = await get_db()
        quote = await db.quotes.find_one({"id": quote_id})
        
        if not quote:
            raise HTTPException(status_code=404, detail="Quote not found")
        
        # PDF oluştur
        pdf_generator = PDFQuoteGenerator()
        pdf_buffer = pdf_generator.create_quote_pdf(quote)
        
        # Response headers - ensure proper encoding for Turkish characters
        safe_filename = quote["name"].encode('ascii', 'ignore').decode('ascii')
        if not safe_filename:
            safe_filename = "teklif"
        
        headers = {
            'Content-Type': 'application/pdf',
            'Content-Disposition': f'attachment; filename="{safe_filename}.pdf"'
        }
        
        return StreamingResponse(
            BytesIO(pdf_buffer.read()),
            media_type='application/pdf',
            headers=headers
        )
        
    except Exception as e:
        logger.error(f"Error generating PDF: {e}")
        raise HTTPException(status_code=500, detail=f"Error generating PDF: {str(e)}")

# Category endpoints
@api_router.post("/categories", response_model=Category)
async def create_category(category: CategoryCreate):
    """Create a new category"""
    try:
        category_dict = {
            "id": str(uuid.uuid4()),
            "name": category.name,
            "description": category.description,
            "color": category.color or "#3B82F6",  # Default blue color
            "created_at": datetime.now(timezone.utc)
        }
        
        result = await db.categories.insert_one(category_dict)
        return Category(**category_dict)
        
    except Exception as e:
        logger.error(f"Error creating category: {e}")
        raise HTTPException(status_code=500, detail="Kategori oluşturulamadı")

@api_router.get("/categories", response_model=List[Category])
async def get_categories():
    """Get all categories"""
    try:
        categories = await db.categories.find().to_list(None)
        return [Category(**category) for category in categories]
    except Exception as e:
        logger.error(f"Error getting categories: {e}")
        raise HTTPException(status_code=500, detail="Kategoriler getirilemedi")

@api_router.patch("/categories/{category_id}")
async def update_category(category_id: str, update_data: CategoryCreate):
    """Update a category"""
    try:
        update_dict = {}
        if update_data.name:
            update_dict["name"] = update_data.name
        if update_data.description is not None:
            update_dict["description"] = update_data.description
        if update_data.color:
            update_dict["color"] = update_data.color
        
        if update_dict:
            result = await db.categories.update_one(
                {"id": category_id},
                {"$set": update_dict}
            )
            
            if result.modified_count == 0:
                raise HTTPException(status_code=404, detail="Kategori bulunamadı")
        
        # Get updated category
        updated_category = await db.categories.find_one({"id": category_id})
        return {
            "success": True,
            "message": "Kategori başarıyla güncellendi",
            "category": Category(**updated_category) if updated_category else None
        }
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error updating category: {e}")
        raise HTTPException(status_code=500, detail="Kategori güncellenemedi")

@api_router.delete("/categories/{category_id}")
async def delete_category(category_id: str):
    """Delete a category"""
    try:
        # First, remove category from all products
        await db.products.update_many(
            {"category_id": category_id},
            {"$unset": {"category_id": ""}}
        )
        
        # Then delete the category
        result = await db.categories.delete_one({"id": category_id})
        if result.deleted_count == 0:
            raise HTTPException(status_code=404, detail="Kategori bulunamadı")
        
        return {"success": True, "message": "Kategori silindi"}
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error deleting category: {e}")
        raise HTTPException(status_code=500, detail="Kategori silinemedi")

@api_router.post("/products/{product_id}/assign-category")
async def assign_product_to_category(product_id: str, category_id: str = None):
    """Assign a product to a category"""
    try:
        update_dict = {"category_id": category_id} if category_id else {"$unset": {"category_id": ""}}
        
        result = await db.products.update_one(
            {"id": product_id},
            update_dict if category_id else {"$unset": {"category_id": ""}}
        )
        
        if result.modified_count == 0:
            raise HTTPException(status_code=404, detail="Ürün bulunamadı")
        
        return {"success": True, "message": "Ürün kategoriye atandı"}
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error assigning product to category: {e}")
        raise HTTPException(status_code=500, detail="Ürün kategoriye atanamadı")

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
        
        # Try color-based parsing first, then fall back to traditional parsing
        try:
            # Color-based parsing
            products_data = ColorBasedExcelService.parse_colored_excel(file_content, company['name'])
            logger.info(f"Color-based parsing successful: {len(products_data)} products")
        except Exception as color_parse_error:
            logger.warning(f"Color-based parsing failed: {color_parse_error}")
            # Fall back to traditional parsing
            products_data = excel_service.parse_excel_file(file_content)
            logger.info(f"Traditional parsing used: {len(products_data)} products")
        
        if not products_data:
            raise HTTPException(status_code=400, detail="Excel dosyasında geçerli ürün verisi bulunamadı")
        
        # Get current exchange rates
        await currency_service.get_exchange_rates()
        
        # Process and save products
        created_products = []
        for product_data in products_data:
            try:
                # Handle company management for color-based parsing
                target_company_id = company_id
                
                # If product has a different company name (from color-based parsing)
                if (product_data.get('company_name') and 
                    product_data['company_name'] != company['name'] and
                    product_data['company_name'] != "Unknown"):
                    
                    # Check if this company already exists
                    existing_company = await db.companies.find_one({"name": product_data['company_name']})
                    if existing_company:
                        target_company_id = existing_company['id']
                    else:
                        # Create new company
                        new_company_dict = {
                            "id": str(uuid.uuid4()),
                            "name": product_data['company_name'],
                            "created_at": datetime.now(timezone.utc)
                        }
                        await db.companies.insert_one(new_company_dict)
                        target_company_id = new_company_dict['id']
                        logger.info(f"Created new company: {product_data['company_name']}")
                
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
                    "company_id": target_company_id,
                    "description": product_data.get('description'),
                    "image_url": None,  # Will be added later if needed
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
async def get_products(
    company_id: Optional[str] = None,
    category_id: Optional[str] = None,
    search: Optional[str] = None
):
    """Get all products, optionally filtered by company, category, or search term"""
    try:
        query = {}
        if company_id:
            query["company_id"] = company_id
        if category_id:
            query["category_id"] = category_id
        if search:
            # Case-insensitive search in product name
            query["name"] = {"$regex": search, "$options": "i"}
            
        products = await db.products.find(query).to_list(None)
        return [Product(**product) for product in products]
    except Exception as e:
        logger.error(f"Error getting products: {e}")
        raise HTTPException(status_code=500, detail="Ürünler getirilemedi")

@api_router.post("/products", response_model=Product)
async def create_product(product: ProductCreate):
    """Create a new product manually"""
    try:
        # Verify company exists
        company = await db.companies.find_one({"id": product.company_id})
        if not company:
            raise HTTPException(status_code=404, detail="Firma bulunamadı")
        
        # Verify category exists (if provided)
        if product.category_id:
            category = await db.categories.find_one({"id": product.category_id})
            if not category:
                raise HTTPException(status_code=404, detail="Kategori bulunamadı")
        
        # Get current exchange rates for TRY conversion
        await currency_service.get_exchange_rates()
        
        # Convert prices to TRY
        try:
            list_price_try = await currency_service.convert_to_try(
                product.list_price, 
                product.currency
            )
        except Exception as e:
            logger.warning(f"Failed to convert price to TRY for product {product.name}: {e}")
            # Fallback: Use original price as TRY if conversion fails
            list_price_try = product.list_price
        
        discounted_price_try = None
        if product.discounted_price:
            try:
                discounted_price_try = await currency_service.convert_to_try(
                    product.discounted_price, 
                    product.currency
                )
            except Exception as e:
                logger.warning(f"Failed to convert discounted price to TRY for product {product.name}: {e}")
                discounted_price_try = product.discounted_price
        
        # Create product
        product_dict = {
            "id": str(uuid.uuid4()),
            "name": product.name,
            "company_id": product.company_id,
            "category_id": product.category_id,
            "description": product.description,
            "image_url": product.image_url,
            "list_price": float(product.list_price),
            "discounted_price": float(product.discounted_price) if product.discounted_price else None,
            "currency": product.currency.upper(),
            "list_price_try": float(list_price_try),
            "discounted_price_try": float(discounted_price_try) if discounted_price_try else None,
            "created_at": datetime.now(timezone.utc)
        }
        
        await db.products.insert_one(product_dict)
        
        return Product(**product_dict)
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error creating product: {e}")
        raise HTTPException(status_code=500, detail="Ürün oluşturulamadı")



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