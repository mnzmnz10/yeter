#!/usr/bin/env python3
"""
MongoDB Atlas Migration Script
Bu script mevcut local MongoDB verilerini Atlas'a taşır
"""

import pymongo
from pymongo import MongoClient
import os
from datetime import datetime

print("🚀 MongoDB Atlas Migration Başlıyor...")
print("=" * 50)

# Local MongoDB (mevcut veriler)
LOCAL_URI = "mongodb://localhost:27017"
DATABASE_NAME = "karavan_db"

# Atlas MongoDB (YENİ - Atlas connection string'inizi buraya girin)
# ATLAS_URI değişkenini aşağıdaki gibi doldurun:
# mongodb+srv://username:password@cluster0.xxxxx.mongodb.net/?retryWrites=true&w=majority

ATLAS_URI = ""  # BURAYA ATLAS CONNECTION STRING'İNİZİ GİRİN

if not ATLAS_URI:
    print("❌ Hata: ATLAS_URI değişkenini script içinde doldurmanız gerekiyor!")
    print("📝 Lütfen migrate_to_atlas.py dosyasını editleyip ATLAS_URI değişkenine connection string'inizi yazın")
    print("💡 Örnek: ATLAS_URI = 'mongodb+srv://username:password@cluster0.xxxxx.mongodb.net/?retryWrites=true&w=majority'")
    exit(1)

try:
    # Bağlantıları test et
    print("\n📡 Bağlantılar test ediliyor...")
    
    # Local bağlantı
    local_client = MongoClient(LOCAL_URI)
    local_db = local_client[DATABASE_NAME]
    local_client.admin.command('ping')
    print("✅ Local MongoDB bağlantısı başarılı")
    
    # Atlas bağlantı
    atlas_client = MongoClient(ATLAS_URI)
    atlas_db = atlas_client[DATABASE_NAME]
    atlas_client.admin.command('ping')
    print("✅ MongoDB Atlas bağlantısı başarılı")
    
    # Mevcut collections'ları listele
    collections = local_db.list_collection_names()
    print(f"\n📂 Bulunan Collections: {collections}")
    print(f"📊 Toplam {len(collections)} collection taşınacak")
    
    # Her collection için migration
    total_documents = 0
    migration_summary = []
    
    for collection_name in collections:
        print(f"\n🔄 Taşınıyor: {collection_name}")
        
        # Local'den veri oku
        local_collection = local_db[collection_name]
        documents = list(local_collection.find())
        
        if documents:
            # Atlas'ta collection var mı kontrol et
            atlas_collection = atlas_db[collection_name]
            existing_count = atlas_collection.count_documents({})
            
            if existing_count > 0:
                overwrite = input(f"⚠️  '{collection_name}' Atlas'ta zaten var ({existing_count} kayıt). Üzerine yazılsın mı? (y/n): ")
                if overwrite.lower() == 'y':
                    atlas_collection.drop()
                    print(f"🗑️  Mevcut {collection_name} silindi")
                else:
                    print(f"⏭️  {collection_name} atlandı")
                    continue
            
            # Atlas'a veri yaz
            try:
                result = atlas_collection.insert_many(documents)
                inserted_count = len(result.inserted_ids)
                total_documents += inserted_count
                
                print(f"✅ {inserted_count} kayıt başarıyla taşındı")
                migration_summary.append({
                    'collection': collection_name,
                    'count': inserted_count,
                    'status': 'success'
                })
                
            except Exception as e:
                print(f"❌ Hata: {collection_name} taşınırken hata: {e}")
                migration_summary.append({
                    'collection': collection_name,
                    'count': 0,
                    'status': f'error: {e}'
                })
        else:
            print(f"⚠️  {collection_name} boş - atlandı")
            migration_summary.append({
                'collection': collection_name,
                'count': 0,
                'status': 'empty'
            })
    
    # Migration özeti
    print("\n" + "=" * 50)
    print("🎉 MIGRATION TAMAMLANDI!")
    print("=" * 50)
    print(f"📊 Toplam taşınan kayıt: {total_documents}")
    print(f"📅 Tarih: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    
    print("\n📋 Detaylı Özet:")
    for item in migration_summary:
        status_emoji = "✅" if item['status'] == 'success' else "⚠️" if item['status'] == 'empty' else "❌"
        print(f"  {status_emoji} {item['collection']}: {item['count']} kayıt ({item['status']})")
    
    # Atlas database durumu
    print(f"\n🔍 Atlas Veritabanı Durumu:")
    atlas_collections = atlas_db.list_collection_names()
    for col_name in atlas_collections:
        count = atlas_db[col_name].count_documents({})
        print(f"  📁 {col_name}: {count} kayıt")
    
    print(f"\n✨ Migration başarıyla tamamlandı!")
    print(f"🔗 Atlas URI: {ATLAS_URI.split('@')[1] if '@' in ATLAS_URI else 'Gizli'}")
    
except Exception as e:
    print(f"❌ HATA: {e}")
    print("🔧 Lütfen connection string'inizi ve network erişimini kontrol edin")
    
finally:
    # Bağlantıları kapat
    try:
        local_client.close()
        atlas_client.close()
        print("🔒 Bağlantılar kapatıldı")
    except:
        pass