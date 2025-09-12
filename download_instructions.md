# MongoDB Atlas Import Talimatları

## 📥 JSON Dosyalarını İndirme

Dosyalar bu chat ortamında çok büyük olduğu için aşağıdaki yöntemlerden birini kullanın:

### Yöntem 1: Atlas Web Interface (Önerilen)
1. MongoDB Atlas Dashboard → Cluster seçin
2. Collections → Create Database → `karavan_db`
3. Her collection için JSON'ı kopyala-yapıştır

### Yöntem 2: MongoDB Compass (GUI)
1. MongoDB Compass indir
2. Atlas connection string ile bağlan
3. Import Data → JSON files

### Yöntem 3: Command Line (Kendi bilgisayarınızdan)
```bash
# MongoDB Tools kurulduktan sonra:
mongoimport --uri="mongodb+srv://corlukaravan:mnzmnz10@corlukaravanteklif.gjnsd46.mongodb.net/karavan_db" --collection categories --jsonArray --file categories.json
mongoimport --uri="mongodb+srv://corlukaravan:mnzmnz10@corlukaravanteklif.gjnsd46.mongodb.net/karavan_db" --collection companies --jsonArray --file companies.json
mongoimport --uri="mongodb+srv://corlukaravan:mnzmnz10@corlukaravanteklif.gjnsd46.mongodb.net/karavan_db" --collection exchange_rates --jsonArray --file exchange_rates.json
mongoimport --uri="mongodb+srv://corlukaravan:mnzmnz10@corlukaravanteklif.gjnsd46.mongodb.net/karavan_db" --collection products --jsonArray --file products.json
mongoimport --uri="mongodb+srv://corlukaravan:mnzmnz10@corlukaravanteklif.gjnsd46.mongodb.net/karavan_db" --collection quotes --jsonArray --file quotes.json
mongoimport --uri="mongodb+srv://corlukaravan:mnzmnz10@corlukaravanteklif.gjnsd46.mongodb.net/karavan_db" --collection upload_history --jsonArray --file upload_history.json
```

## 📊 Import Özeti:
- **categories**: 6 kayıt
- **companies**: 3 kayıt  
- **exchange_rates**: 4 kayıt
- **products**: 443 kayıt (en büyük)
- **quotes**: 43 kayıt
- **upload_history**: 4 kayıt

**Toplam: 503 kayıt**

## ✅ Import Sonrası:
Backend .env dosyasını Atlas connection string ile güncelleyin:
```
MONGO_URL=mongodb+srv://corlukaravan:mnzmnz10@corlukaravanteklif.gjnsd46.mongodb.net/
DB_NAME=karavan_db
```