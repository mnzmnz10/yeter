import React, { useState, useEffect } from 'react';
import './App.css';
import axios from 'axios';
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from './components/ui/card';
import { Button } from './components/ui/button';
import { Input } from './components/ui/input';
import { Label } from './components/ui/label';
import { Table, TableBody, TableCell, TableHead, TableHeader, TableRow } from './components/ui/table';
import { Badge } from './components/ui/badge';
import { Tabs, TabsContent, TabsList, TabsTrigger } from './components/ui/tabs';
import { Dialog, DialogContent, DialogDescription, DialogFooter, DialogHeader, DialogTitle, DialogTrigger } from './components/ui/dialog';
import { Select, SelectContent, SelectItem, SelectTrigger, SelectValue } from './components/ui/select';
import { Trash2, Upload, RefreshCw, Plus, TrendingUp, Building2, Package, DollarSign, Edit, Save, X } from 'lucide-react';
import { toast } from 'sonner';
import { Toaster } from './components/ui/sonner';

const BACKEND_URL = process.env.REACT_APP_BACKEND_URL;
const API = `${BACKEND_URL}/api`;

function App() {
  const [companies, setCompanies] = useState([]);
  const [products, setProducts] = useState([]);
  const [comparisonData, setComparisonData] = useState([]);
  const [exchangeRates, setExchangeRates] = useState({});
  const [loading, setLoading] = useState(false);
  const [selectedCompany, setSelectedCompany] = useState('');
  const [newCompanyName, setNewCompanyName] = useState('');
  const [uploadFile, setUploadFile] = useState(null);
  const [stats, setStats] = useState({
    totalCompanies: 0,
    totalProducts: 0,
    totalMatches: 0
  });
  const [editingProduct, setEditingProduct] = useState(null);
  const [editForm, setEditForm] = useState({
    name: '',
    list_price: '',
    discounted_price: '',
    currency: ''
  });

  // Load initial data
  useEffect(() => {
    loadInitialData();
  }, []);

  const loadInitialData = async () => {
    setLoading(true);
    try {
      await Promise.all([
        loadCompanies(),
        loadProducts(),
        loadComparisonData(),
        loadExchangeRates()
      ]);
    } catch (error) {
      console.error('Error loading initial data:', error);
      toast.error('Veri yüklenirken hata oluştu');
    } finally {
      setLoading(false);
    }
  };

  const loadCompanies = async () => {
    try {
      const response = await axios.get(`${API}/companies`);
      setCompanies(response.data);
      setStats(prev => ({ ...prev, totalCompanies: response.data.length }));
    } catch (error) {
      console.error('Error loading companies:', error);
      toast.error('Firmalar yüklenemedi');
    }
  };

  const loadProducts = async () => {
    try {
      const response = await axios.get(`${API}/products`);
      setProducts(response.data);
      setStats(prev => ({ ...prev, totalProducts: response.data.length }));
    } catch (error) {
      console.error('Error loading products:', error);
      toast.error('Ürünler yüklenemedi');
    }
  };

  const loadComparisonData = async () => {
    try {
      const response = await axios.get(`${API}/products/comparison`);
      setComparisonData(response.data.comparison_data || []);
      setStats(prev => ({ ...prev, totalMatches: response.data.comparison_data?.length || 0 }));
    } catch (error) {
      console.error('Error loading comparison data:', error);
      toast.error('Karşılaştırma verileri yüklenemedi');
    }
  };

  const loadExchangeRates = async () => {
    try {
      const response = await axios.get(`${API}/exchange-rates`);
      if (response.data.success) {
        setExchangeRates(response.data.rates);
      }
    } catch (error) {
      console.error('Error loading exchange rates:', error);
      toast.error('Döviz kurları yüklenemedi');
    }
  };

  const createCompany = async () => {
    if (!newCompanyName.trim()) {
      toast.error('Firma adı gerekli');
      return;
    }

    try {
      await axios.post(`${API}/companies`, { name: newCompanyName });
      setNewCompanyName('');
      await loadCompanies();
      toast.success('Firma başarıyla oluşturuldu');
    } catch (error) {
      console.error('Error creating company:', error);
      toast.error('Firma oluşturulamadı');
    }
  };

  const deleteCompany = async (companyId) => {
    try {
      await axios.delete(`${API}/companies/${companyId}`);
      await loadCompanies();
      await loadProducts();
      toast.success('Firma silindi');
    } catch (error) {
      console.error('Error deleting company:', error);
      toast.error('Firma silinemedi');
    }
  };

  const uploadExcelFile = async () => {
    if (!selectedCompany || !uploadFile) {
      toast.error('Firma seçin ve dosya yükleyin');
      return;
    }

    const formData = new FormData();
    formData.append('file', uploadFile);

    try {
      setLoading(true);
      const response = await axios.post(`${API}/companies/${selectedCompany}/upload-excel`, formData, {
        headers: { 'Content-Type': 'multipart/form-data' }
      });
      
      setUploadFile(null);
      setSelectedCompany('');
      await loadProducts();
      toast.success(response.data.message);
    } catch (error) {
      console.error('Error uploading file:', error);
      toast.error(error.response?.data?.detail || 'Dosya yüklenemedi');
    } finally {
      setLoading(false);
    }
  };

  const refreshPrices = async () => {
    try {
      setLoading(true);
      const response = await axios.post(`${API}/refresh-prices`);
      await loadProducts();
      await loadExchangeRates();
      toast.success(response.data.message);
    } catch (error) {
      console.error('Error refreshing prices:', error);
      toast.error('Fiyatlar güncellenemedi');
    } finally {
      setLoading(false);
    }
  };

  const formatPrice = (price) => {
    return new Intl.NumberFormat('tr-TR', { 
      style: 'decimal', 
      minimumFractionDigits: 2 
    }).format(price);
  };

  const getCurrencySymbol = (currency) => {
    const symbols = {
      'TRY': '₺',
      'USD': '$',
      'EUR': '€',
      'GBP': '£'
    };
    return symbols[currency] || currency;
  };

  const StatsCard = ({ title, value, icon: Icon, description }) => (
    <Card className="bg-gradient-to-br from-emerald-50 to-teal-50 border-emerald-200">
      <CardHeader className="flex flex-row items-center justify-between space-y-0 pb-2">
        <CardTitle className="text-sm font-medium text-emerald-800">{title}</CardTitle>
        <Icon className="h-4 w-4 text-emerald-600" />
      </CardHeader>
      <CardContent>
        <div className="text-2xl font-bold text-emerald-900">{value}</div>
        <p className="text-xs text-emerald-600 mt-1">{description}</p>
      </CardContent>
    </Card>
  );

  return (
    <div className="min-h-screen bg-gradient-to-br from-slate-50 via-emerald-25 to-teal-50">
      <div className="container mx-auto p-6 max-w-7xl">
        {/* Header */}
        <div className="mb-8">
          <h1 className="text-4xl font-bold text-slate-800 mb-2">
            Karavan Elektrik Ekipmanları
          </h1>
          <p className="text-lg text-slate-600">Fiyat Karşılaştırma Sistemi</p>
        </div>

        {/* Stats Cards */}
        <div className="grid grid-cols-1 md:grid-cols-4 gap-6 mb-8">
          <StatsCard
            title="Toplam Firma"
            value={stats.totalCompanies}
            icon={Building2}
            description="Kayıtlı tedarikçi sayısı"
          />
          <StatsCard
            title="Toplam Ürün"
            value={stats.totalProducts}
            icon={Package}
            description="Sisteme yüklenmiş ürün"
          />
          <StatsCard
            title="Eşleştirme"
            value={stats.totalMatches}
            icon={TrendingUp}
            description="Karşılaştırma grubu"
          />
          <Card className="bg-gradient-to-br from-emerald-50 to-teal-50 border-emerald-200">
            <CardHeader className="flex flex-row items-center justify-between space-y-0 pb-2">
              <CardTitle className="text-sm font-medium text-emerald-800">Döviz Kurları</CardTitle>
              <DollarSign className="h-4 w-4 text-emerald-600" />
            </CardHeader>
            <CardContent>
              <div className="space-y-1">
                <div className="flex justify-between items-center">
                  <span className="text-sm text-emerald-700">USD/TRY:</span>
                  <span className="text-lg font-bold text-emerald-900">
                    {exchangeRates.USD ? formatPrice(exchangeRates.USD) : '---'}
                  </span>
                </div>
                <div className="flex justify-between items-center">
                  <span className="text-sm text-emerald-700">EUR/TRY:</span>
                  <span className="text-lg font-bold text-emerald-900">
                    {exchangeRates.EUR ? formatPrice(exchangeRates.EUR) : '---'}
                  </span>
                </div>
              </div>
              <p className="text-xs text-emerald-600 mt-1">Güncel döviz kurları</p>
            </CardContent>
          </Card>
        </div>

        {/* Action Buttons */}
        <div className="flex flex-wrap gap-4 mb-8">
          <Button 
            onClick={refreshPrices} 
            disabled={loading}
            className="bg-emerald-600 hover:bg-emerald-700 text-white"
          >
            <RefreshCw className={`w-4 h-4 mr-2 ${loading ? 'animate-spin' : ''}`} />
            Kurları Güncelle
          </Button>
        </div>

        <Tabs defaultValue="companies" className="space-y-6">
          <TabsList className="grid w-full grid-cols-4">
            <TabsTrigger value="companies">Firmalar</TabsTrigger>
            <TabsTrigger value="upload">Excel Yükle</TabsTrigger>
            <TabsTrigger value="products">Ürünler</TabsTrigger>
            <TabsTrigger value="comparison">Karşılaştırma</TabsTrigger>
          </TabsList>

          {/* Companies Tab */}
          <TabsContent value="companies" className="space-y-6">
            <Card>
              <CardHeader>
                <CardTitle>Firma Yönetimi</CardTitle>
                <CardDescription>Tedarikçi firmalarınızı ekleyin ve yönetin</CardDescription>
              </CardHeader>
              <CardContent>
                <div className="flex gap-4 mb-6">
                  <Input
                    placeholder="Firma adı"
                    value={newCompanyName}
                    onChange={(e) => setNewCompanyName(e.target.value)}
                    className="flex-1"
                  />
                  <Button onClick={createCompany}>
                    <Plus className="w-4 h-4 mr-2" />
                    Firma Ekle
                  </Button>
                </div>

                <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-4">
                  {companies.map((company) => (
                    <Card key={company.id} className="border-slate-200">
                      <CardHeader className="pb-3">
                        <CardTitle className="text-lg">{company.name}</CardTitle>
                        <CardDescription>
                          {new Date(company.created_at).toLocaleDateString('tr-TR')}
                        </CardDescription>
                      </CardHeader>
                      <CardContent className="pt-0">
                        <Button
                          variant="destructive"
                          size="sm"
                          onClick={() => deleteCompany(company.id)}
                        >
                          <Trash2 className="w-4 h-4 mr-2" />
                          Sil
                        </Button>
                      </CardContent>
                    </Card>
                  ))}
                </div>
              </CardContent>
            </Card>
          </TabsContent>

          {/* Upload Tab */}
          <TabsContent value="upload" className="space-y-6">
            <Card>
              <CardHeader>
                <CardTitle>Excel Dosyası Yükle</CardTitle>
                <CardDescription>
                  Ürün fiyat listelerinizi Excel formatında yükleyin
                  <br />
                  <span className="text-sm text-amber-600">
                    Beklenen kolonlar: Ürün Adı, Liste Fiyatı, İndirimli Fiyat, Para Birimi
                  </span>
                </CardDescription>
              </CardHeader>
              <CardContent>
                <div className="space-y-4">
                  <div>
                    <Label htmlFor="company-select">Firma Seçin</Label>
                    <Select value={selectedCompany} onValueChange={setSelectedCompany}>
                      <SelectTrigger>
                        <SelectValue placeholder="Firma seçin" />
                      </SelectTrigger>
                      <SelectContent>
                        {companies.map((company) => (
                          <SelectItem key={company.id} value={company.id}>
                            {company.name}
                          </SelectItem>
                        ))}
                      </SelectContent>
                    </Select>
                  </div>

                  <div>
                    <Label htmlFor="file-upload">Excel Dosyası</Label>
                    <Input
                      id="file-upload"
                      type="file"
                      accept=".xlsx,.xls"
                      onChange={(e) => setUploadFile(e.target.files[0])}
                    />
                  </div>

                  <Button 
                    onClick={uploadExcelFile} 
                    disabled={loading || !selectedCompany || !uploadFile}
                    className="w-full"
                  >
                    <Upload className="w-4 h-4 mr-2" />
                    {loading ? 'Yükleniyor...' : 'Excel Dosyası Yükle'}
                  </Button>
                </div>
              </CardContent>
            </Card>
          </TabsContent>

          {/* Products Tab */}
          <TabsContent value="products" className="space-y-6">
            <Card>
              <CardHeader>
                <CardTitle>Ürün Listesi</CardTitle>
                <CardDescription>Tüm yüklenmiş ürünler ve fiyatları</CardDescription>
              </CardHeader>
              <CardContent>
                <div className="overflow-x-auto">
                  <Table>
                    <TableHeader>
                      <TableRow>
                        <TableHead>Ürün Adı</TableHead>
                        <TableHead>Firma</TableHead>
                        <TableHead>Liste Fiyatı</TableHead>
                        <TableHead>İndirimli Fiyat</TableHead>
                        <TableHead>Para Birimi</TableHead>
                        <TableHead>TL Fiyat</TableHead>
                        <TableHead>TL İndirimli</TableHead>
                      </TableRow>
                    </TableHeader>
                    <TableBody>
                      {products.map((product) => {
                        const company = companies.find(c => c.id === product.company_id);
                        return (
                          <TableRow key={product.id}>
                            <TableCell className="font-medium">{product.name}</TableCell>
                            <TableCell>
                              <Badge variant="outline">{company?.name || 'Unknown'}</Badge>
                            </TableCell>
                            <TableCell>
                              {getCurrencySymbol(product.currency)} {formatPrice(product.list_price)}
                            </TableCell>
                            <TableCell>
                              {product.discounted_price ? (
                                `${getCurrencySymbol(product.currency)} ${formatPrice(product.discounted_price)}`
                              ) : '-'}
                            </TableCell>
                            <TableCell>
                              <Badge>{product.currency}</Badge>
                            </TableCell>
                            <TableCell>
                              ₺ {product.list_price_try ? formatPrice(product.list_price_try) : '---'}
                            </TableCell>
                            <TableCell>
                              {product.discounted_price_try ? (
                                `₺ ${formatPrice(product.discounted_price_try)}`
                              ) : '-'}
                            </TableCell>
                          </TableRow>
                        );
                      })}
                    </TableBody>
                  </Table>
                </div>
              </CardContent>
            </Card>
          </TabsContent>

          {/* Comparison Tab */}
          <TabsContent value="comparison" className="space-y-6">
            <Card>
              <CardHeader>
                <CardTitle>Fiyat Karşılaştırması</CardTitle>
                <CardDescription>
                  Eşleştirdiğiniz ürünlerin fiyat karşılaştırması
                  <br />
                  <span className="text-sm text-amber-600">
                    Henüz karşılaştırma özelliği geliştirilmektedir. Şu an için ürün listesini inceleyebilirsiniz.
                  </span>
                </CardDescription>
              </CardHeader>
              <CardContent>
                {comparisonData.length > 0 ? (
                  <div className="space-y-6">
                    {comparisonData.map((comparison) => (
                      <Card key={comparison.id} className="border-emerald-200">
                        <CardHeader>
                          <CardTitle className="text-lg">{comparison.product_name}</CardTitle>
                        </CardHeader>
                        <CardContent>
                          <Table>
                            <TableHeader>
                              <TableRow>
                                <TableHead>Firma</TableHead>
                                <TableHead>Liste Fiyatı (TL)</TableHead>
                                <TableHead>İndirimli Fiyat (TL)</TableHead>
                                <TableHead>Orijinal Para Birimi</TableHead>
                              </TableRow>
                            </TableHeader>
                            <TableBody>
                              {comparison.products.map((product) => (
                                <TableRow key={product.id}>
                                  <TableCell>
                                    <Badge variant="outline">{product.company_name}</Badge>
                                  </TableCell>
                                  <TableCell>
                                    ₺ {formatPrice(product.list_price_try)}
                                  </TableCell>
                                  <TableCell>
                                    {product.discounted_price_try ? (
                                      `₺ ${formatPrice(product.discounted_price_try)}`
                                    ) : '-'}
                                  </TableCell>
                                  <TableCell>
                                    {getCurrencySymbol(product.currency)} {formatPrice(product.list_price)}
                                  </TableCell>
                                </TableRow>
                              ))}
                            </TableBody>
                          </Table>
                        </CardContent>
                      </Card>
                    ))}
                  </div>
                ) : (
                  <div className="text-center py-12 text-slate-500">
                    <Package className="w-16 h-16 mx-auto mb-4 opacity-50" />
                    <p className="text-lg">Henüz karşılaştırma verisi bulunmuyor</p>
                    <p className="text-sm">Excel dosyalarınızı yükledikten sonra ürün eşleştirmeleri yapabilirsiniz</p>
                  </div>
                )}
              </CardContent>
            </Card>
          </TabsContent>
        </Tabs>
      </div>
      <Toaster position="top-right" />
    </div>
  );
}

export default App;