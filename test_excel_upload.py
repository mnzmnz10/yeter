import requests
import pandas as pd
import io
import json
from datetime import datetime

# Test verisi oluştur
test_data = {
    'Ürün Adı': [
        'Solar Panel 300W',
        'Invertör 5kW', 
        'Batarya 100Ah',
        'Şarj Kontrol Cihazı',
        'Kablo Set'
    ],
    'Liste Fiyatı': [1500, 3200, 800, 450, 150],
    'İndirimli Fiyat': [1350, 2880, 720, 405, 135],
    'Para Birimi': ['USD', 'USD', 'EUR', 'TRY', 'TRY']
}

# DataFrame oluştur
df = pd.DataFrame(test_data)

# Excel dosyası oluştur (memory'de)
excel_buffer = io.BytesIO()
df.to_excel(excel_buffer, index=False, sheet_name='Ürünler')
excel_buffer.seek(0)

# API endpoint
API_BASE = "https://039781ab-c520-4927-8b4a-9e1599f54130.preview.emergentagent.com/api"
COMPANY_ID = "fdd84f9d-4276-41aa-afeb-4637879f30c3"  # Test Firma Bağlantı

# Excel dosyasını yükle
files = {
    'file': ('test_urunler.xlsx', excel_buffer.getvalue(), 'application/vnd.openxmlformats-officedocument.spreadsheetml.sheet')
}

print("📤 Excel dosyası yükleniyor...")
print(f"🏢 Firma: Test Firma Bağlantı")
print(f"📊 Ürün sayısı: {len(test_data['Ürün Adı'])}")
print("=" * 50)

try:
    response = requests.post(
        f"{API_BASE}/companies/{COMPANY_ID}/upload-excel",
        files=files,
        timeout=30
    )
    
    print(f"📡 API Response Status: {response.status_code}")
    
    if response.status_code == 200:
        result = response.json()
        print("✅ Upload başarılı!")
        print(f"📋 Mesaj: {result.get('message', 'N/A')}")
        
        if 'summary' in result:
            summary = result['summary']
            print(f"📊 Toplam ürün: {summary.get('total_products', 0)}")
            print(f"🆕 Yeni ürün: {summary.get('new_products', 0)}")
            print(f"🔄 Güncellenmiş ürün: {summary.get('updated_products', 0)}")
            print(f"💰 Fiyat değişimi: {summary.get('price_changes', 0)}")
            
            if 'currency_distribution' in summary:
                print("💱 Para birimi dağılımı:")
                for currency, count in summary['currency_distribution'].items():
                    print(f"   {currency}: {count} ürün")
        
        # Upload geçmişini kontrol et
        print("\n" + "=" * 50)
        print("📚 Upload geçmişi kontrol ediliyor...")
        
        history_response = requests.get(f"{API_BASE}/companies/{COMPANY_ID}/upload-history")
        if history_response.status_code == 200:
            history = history_response.json()
            print(f"📜 Toplam upload: {len(history)}")
            if history:
                latest = history[0]  # En son upload
                print(f"📅 Son upload: {latest['filename']}")
                print(f"🕐 Tarih: {latest['upload_date']}")
                print(f"📊 İstatistikler: {latest['total_products']} toplam, {latest['new_products']} yeni, {latest['updated_products']} güncellenmiş")
                if latest.get('price_changes'):
                    print(f"💰 Fiyat değişiklikleri: {len(latest['price_changes'])} adet")
        else:
            print(f"❌ Upload geçmişi alınamadı: {history_response.status_code}")
            
    else:
        print(f"❌ Upload başarısız: {response.status_code}")
        print(f"🔍 Hata detayı: {response.text}")
        
except Exception as e:
    print(f"❌ Hata oluştu: {str(e)}")

print("=" * 50)
print("🎯 Test tamamlandı!")