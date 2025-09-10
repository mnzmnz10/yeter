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
import { Trash2, Upload, RefreshCw, Plus, TrendingUp, Building2, Package, DollarSign, Edit, Save, X, FileText, Check, Archive, Download, Wrench } from 'lucide-react';
import { toast } from 'sonner';
import { Toaster } from './components/ui/sonner';

const BACKEND_URL = process.env.REACT_APP_BACKEND_URL;
const API = `${BACKEND_URL}/api`;

function App() {
  const [companies, setCompanies] = useState([]);
  const [products, setProducts] = useState([]);

  const [exchangeRates, setExchangeRates] = useState({});
  const [loading, setLoading] = useState(false);
  const [selectedCompany, setSelectedCompany] = useState('');
  const [newCompanyName, setNewCompanyName] = useState('');
  const [uploadFile, setUploadFile] = useState(null);
  const [stats, setStats] = useState({
    totalCompanies: 0,
    totalProducts: 0
  });
  const [editingProduct, setEditingProduct] = useState(null);
  const [editForm, setEditForm] = useState({
    name: '',
    description: '',
    image_url: '',
    list_price: '',
    discounted_price: '',
    currency: '',
    category_id: ''
  });
  const [categories, setCategories] = useState([]);
  const [searchQuery, setSearchQuery] = useState('');
  const [selectedCategory, setSelectedCategory] = useState('');
  const [newCategoryName, setNewCategoryName] = useState('');
  const [newCategoryDescription, setNewCategoryDescription] = useState('');
  const [newCategoryColor, setNewCategoryColor] = useState('#3B82F6');
  const [showAddProductDialog, setShowAddProductDialog] = useState(false);
  const [selectedProducts, setSelectedProducts] = useState(new Map()); // Map<productId, quantity>
  const [quoteName, setQuoteName] = useState('');
  const [showCreateQuoteDialog, setShowCreateQuoteDialog] = useState(false);
  const [quoteDiscount, setQuoteDiscount] = useState(0);
  const [quoteLaborCost, setQuoteLaborCost] = useState(0); // İşçilik maliyeti state'i
  const [quotes, setQuotes] = useState([]);
  const [selectedQuote, setSelectedQuote] = useState(null);
  const [quoteSearchTerm, setQuoteSearchTerm] = useState('');
  const [filteredQuotes, setFilteredQuotes] = useState([]);
  const [newProductForm, setNewProductForm] = useState({
    name: '',
    company_id: '',
    category_id: '',
    description: '',
    image_url: '',
    list_price: '',
    discounted_price: '',
    currency: 'USD'
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
        loadCategories(),
        loadExchangeRates(),
        fetchQuotes()
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

  // Quotes değiştiğinde filtreleme yap
  useEffect(() => {
    filterQuotes(quoteSearchTerm);
  }, [quotes]);

  const fetchQuotes = async () => {
    try {
      const response = await fetch(`${API}/quotes`);
      const data = await response.json();
      setQuotes(data);
      setFilteredQuotes(data); // Başlangıçta tüm teklifler görünsün
    } catch (error) {
      console.error('Teklifler yüklenirken hata:', error);
      toast.error('Teklifler yüklenemedi');
    }
  };

  // Teklif arama fonksiyonu
  const filterQuotes = (searchTerm) => {
    if (!searchTerm.trim()) {
      setFilteredQuotes(quotes);
      return;
    }

    const filtered = quotes.filter(quote => {
      const searchLower = searchTerm.toLowerCase();
      
      // Teklif adında ara
      const nameMatch = quote.name.toLowerCase().includes(searchLower);
      
      // Müşteri adında ara (varsa)
      const customerMatch = quote.customer_name && 
        quote.customer_name.toLowerCase().includes(searchLower);
      
      // Teklifteki ürün adlarında ara
      const productMatch = quote.products.some(product => 
        product.name.toLowerCase().includes(searchLower) ||
        product.company_name.toLowerCase().includes(searchLower)
      );
      
      return nameMatch || customerMatch || productMatch;
    });

    setFilteredQuotes(filtered);
  };

  // Arama terimi değiştiğinde filtreleme yap
  const handleQuoteSearch = (searchTerm) => {
    setQuoteSearchTerm(searchTerm);
    filterQuotes(searchTerm);
  };

  const loadProducts = async () => {
    try {
      const params = new URLSearchParams();
      if (searchQuery) params.append('search', searchQuery);
      if (selectedCategory) params.append('category_id', selectedCategory);
      
      const response = await axios.get(`${API}/products?${params.toString()}`);
      setProducts(response.data);
      setStats(prev => ({ ...prev, totalProducts: response.data.length }));
    } catch (error) {
      console.error('Error loading products:', error);
      toast.error('Ürünler yüklenemedi');
    }
  };

  const loadCategories = async () => {
    try {
      const response = await axios.get(`${API}/categories`);
      setCategories(response.data);
    } catch (error) {
      console.error('Error loading categories:', error);
      toast.error('Kategoriler yüklenemedi');
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

  const startEditProduct = (product) => {
    setEditingProduct(product.id);
    setEditForm({
      name: product.name,
      description: product.description || '',
      image_url: product.image_url || '',
      list_price: product.list_price.toString(),
      discounted_price: product.discounted_price ? product.discounted_price.toString() : '',
      currency: product.currency,
      category_id: product.category_id || 'none'
    });
  };

  const cancelEditProduct = () => {
    setEditingProduct(null);
    setEditForm({
      name: '',
      description: '',
      image_url: '',
      list_price: '',
      discounted_price: '',
      currency: '',
      category_id: 'none'
    });
  };

  const saveEditProduct = async () => {
    if (!editingProduct) return;

    try {
      setLoading(true);
      const updateData = {
        name: editForm.name,
        description: editForm.description || null,
        image_url: editForm.image_url || null,
        list_price: parseFloat(editForm.list_price),
        currency: editForm.currency
      };

      if (editForm.discounted_price) {
        updateData.discounted_price = parseFloat(editForm.discounted_price);
      }

      if (editForm.category_id && editForm.category_id !== 'none') {
        updateData.category_id = editForm.category_id;
      } else if (editForm.category_id === 'none') {
        updateData.category_id = null;
      }

      const response = await axios.patch(`${API}/products/${editingProduct}`, updateData);
      
      if (response.data.success) {
        await loadProducts();
        cancelEditProduct();
        toast.success('Ürün başarıyla güncellendi');
      }
    } catch (error) {
      console.error('Error updating product:', error);
      toast.error('Ürün güncellenemedi');
    } finally {
      setLoading(false);
    }
  };

  const deleteProduct = async (productId) => {
    if (!window.confirm('Bu ürünü silmek istediğinizden emin misiniz?')) {
      return;
    }

    try {
      const response = await axios.delete(`${API}/products/${productId}`);
      if (response.data.success) {
        await loadProducts();
        toast.success('Ürün silindi');
      }
    } catch (error) {
      console.error('Error deleting product:', error);
      toast.error('Ürün silinemedi');
    }
  };

  const createCategory = async () => {
    if (!newCategoryName.trim()) {
      toast.error('Kategori adı gerekli');
      return;
    }

    try {
      await axios.post(`${API}/categories`, {
        name: newCategoryName,
        description: newCategoryDescription,
        color: newCategoryColor
      });
      setNewCategoryName('');
      setNewCategoryDescription('');
      setNewCategoryColor('#3B82F6');
      await loadCategories();
      toast.success('Kategori başarıyla oluşturuldu');
    } catch (error) {
      console.error('Error creating category:', error);
      toast.error('Kategori oluşturulamadı');
    }
  };

  const deleteCategory = async (categoryId) => {
    if (!window.confirm('Bu kategoriyi silmek istediğinizden emin misiniz? Kategorideki ürünler kategorsiz kalacak.')) {
      return;
    }

    try {
      await axios.delete(`${API}/categories/${categoryId}`);
      await loadCategories();
      await loadProducts(); // Refresh products to show updated category info
      toast.success('Kategori silindi');
    } catch (error) {
      console.error('Error deleting category:', error);
      toast.error('Kategori silinemedi');
    }
  };

  const handleSearch = (query) => {
    setSearchQuery(query);
  };

  const handleCategoryFilter = (categoryId) => {
    setSelectedCategory(categoryId === 'all' ? '' : categoryId);
  };

  // Search and category filter effects
  React.useEffect(() => {
    const delayedSearch = setTimeout(() => {
      loadProducts();
    }, 300); // Debounce search

    return () => clearTimeout(delayedSearch);
  }, [searchQuery, selectedCategory]);

  const toggleProductSelection = (productId, quantity = 1) => {
    const newSelected = new Map(selectedProducts);
    if (newSelected.has(productId)) {
      if (quantity === 0) {
        newSelected.delete(productId);
      } else {
        newSelected.set(productId, quantity);
      }
    } else {
      if (quantity > 0) {
        newSelected.set(productId, quantity);
      }
    }
    setSelectedProducts(newSelected);
  };

  const clearSelection = () => {
    setSelectedProducts(new Map());
  };

  const selectAllVisible = () => {
    const newSelected = new Map();
    products.forEach(p => newSelected.set(p.id, 1));
    setSelectedProducts(newSelected);
  };

  const getSelectedProductsData = () => {
    return Array.from(selectedProducts.entries()).map(([productId, quantity]) => {
      const product = products.find(p => p.id === productId);
      return product ? { ...product, quantity } : null;
    }).filter(Boolean);
  };

  const calculateQuoteTotals = () => {
    const selectedProductsData = getSelectedProductsData();
    
    const totalListPrice = selectedProductsData.reduce((sum, p) => {
      const price = parseFloat(p.list_price_try) || 0;
      const quantity = p.quantity || 1;
      return sum + (price * quantity);
    }, 0);
    
    const discountAmount = totalListPrice * (parseFloat(quoteDiscount) || 0) / 100;
    const laborCost = parseFloat(quoteLaborCost) || 0;
    const totalNetPrice = totalListPrice - discountAmount + laborCost;
    
    // Toplam ürün adedi hesapla
    const totalQuantity = selectedProductsData.reduce((sum, p) => sum + (p.quantity || 1), 0);
    
    return {
      totalListPrice: isNaN(totalListPrice) ? 0 : totalListPrice,
      discountAmount: isNaN(discountAmount) ? 0 : discountAmount,
      laborCost: isNaN(laborCost) ? 0 : laborCost,
      totalNetPrice: isNaN(totalNetPrice) ? 0 : totalNetPrice,
      productCount: selectedProductsData.length,
      totalQuantity: totalQuantity
    };
  };

  const resetNewProductForm = () => {
    setNewProductForm({
      name: '',
      company_id: '',
      category_id: '',
      description: '',
      image_url: '',
      list_price: '',
      discounted_price: '',
      currency: 'USD'
    });
  };

  const createProduct = async () => {
    if (!newProductForm.name.trim() || !newProductForm.company_id || !newProductForm.list_price) {
      toast.error('Ürün adı, firma ve liste fiyatı gerekli');
      return;
    }

    try {
      setLoading(true);
      const productData = {
        name: newProductForm.name,
        company_id: newProductForm.company_id,
        description: newProductForm.description || null,
        image_url: newProductForm.image_url || null,
        list_price: parseFloat(newProductForm.list_price),
        currency: newProductForm.currency
      };

      if (newProductForm.discounted_price) {
        productData.discounted_price = parseFloat(newProductForm.discounted_price);
      }

      if (newProductForm.category_id && newProductForm.category_id !== 'none') {
        productData.category_id = newProductForm.category_id;
      }

      const response = await axios.post(`${API}/products`, productData);
      
      if (response.data) {
        await loadProducts();
        setShowAddProductDialog(false);
        resetNewProductForm();
        toast.success('Ürün başarıyla eklendi');
      }
    } catch (error) {
      console.error('Error creating product:', error);
      toast.error(error.response?.data?.detail || 'Ürün eklenemedi');
    } finally {
      setLoading(false);
    }
  };

  const formatPrice = (price) => {
    // Handle NaN, null, undefined cases
    if (isNaN(price) || price === null || price === undefined) {
      return '0,00';
    }
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
        <div className="grid grid-cols-1 md:grid-cols-3 gap-6 mb-8">
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

        <Tabs defaultValue="products" className="space-y-6">
          <TabsList className="grid w-full grid-cols-5">
            <TabsTrigger value="products">Ürünler</TabsTrigger>
            <TabsTrigger value="quotes">
              <div className="flex items-center gap-2">
                <FileText className="w-4 h-4" />
                Teklifler
                {selectedProducts.size > 0 && (
                  <Badge variant="secondary" className="ml-1">
                    {selectedProducts.size}
                  </Badge>
                )}
              </div>
            </TabsTrigger>
            <TabsTrigger value="companies">Firmalar</TabsTrigger>
            <TabsTrigger value="categories">Kategoriler</TabsTrigger>
            <TabsTrigger value="upload">Excel Yükle</TabsTrigger>
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

          {/* Categories Tab */}
          <TabsContent value="categories" className="space-y-6">
            <Card>
              <CardHeader>
                <CardTitle>Kategori Yönetimi</CardTitle>
                <CardDescription>Ürünlerinizi kategorilere ayırın ve düzenleyin</CardDescription>
              </CardHeader>
              <CardContent>
                <div className="space-y-4 mb-6">
                  <div className="grid grid-cols-1 md:grid-cols-3 gap-4">
                    <Input
                      placeholder="Kategori adı"
                      value={newCategoryName}
                      onChange={(e) => setNewCategoryName(e.target.value)}
                    />
                    <Input
                      placeholder="Açıklama (opsiyonel)"
                      value={newCategoryDescription}
                      onChange={(e) => setNewCategoryDescription(e.target.value)}
                    />
                    <div className="flex gap-2">
                      <Input
                        type="color"
                        value={newCategoryColor}
                        onChange={(e) => setNewCategoryColor(e.target.value)}
                        className="w-16"
                      />
                      <Button onClick={createCategory} className="flex-1">
                        <Plus className="w-4 h-4 mr-2" />
                        Kategori Ekle
                      </Button>
                    </div>
                  </div>
                </div>

                <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-4">
                  {categories.map((category) => (
                    <Card key={category.id} className="border-slate-200">
                      <CardHeader className="pb-3" style={{borderLeft: `4px solid ${category.color}`}}>
                        <CardTitle className="text-lg flex items-center gap-2">
                          <div 
                            className="w-4 h-4 rounded-full" 
                            style={{backgroundColor: category.color}}
                          ></div>
                          {category.name}
                        </CardTitle>
                        {category.description && (
                          <CardDescription>{category.description}</CardDescription>
                        )}
                      </CardHeader>
                      <CardContent className="pt-0">
                        <div className="flex gap-2">
                          <Button
                            variant="outline"
                            size="sm"
                            onClick={() => handleCategoryFilter(category.id)}
                          >
                            Ürünleri Göster
                          </Button>
                          <Button
                            variant="destructive"
                            size="sm"
                            onClick={() => deleteCategory(category.id)}
                          >
                            <Trash2 className="w-4 h-4" />
                          </Button>
                        </div>
                      </CardContent>
                    </Card>
                  ))}
                </div>

                {/* Category Filter Info */}
                {selectedCategory && (
                  <div className="mt-6 p-4 bg-emerald-50 border border-emerald-200 rounded-lg">
                    <div className="flex items-center justify-between">
                      <span className="text-emerald-800">
                        Kategori filtresi aktif: <strong>{categories.find(c => c.id === selectedCategory)?.name}</strong>
                      </span>
                      <Button 
                        variant="outline" 
                        size="sm" 
                        onClick={() => handleCategoryFilter('')}
                      >
                        Filtreyi Kaldır
                      </Button>
                    </div>
                  </div>
                )}
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
                {/* Action Bar */}
                <div className="flex justify-between items-center mb-4">
                  <div className="flex items-center gap-4">
                    <h3 className="text-lg font-semibold">Ürün Yönetimi</h3>
                    {selectedProducts.size > 0 && (
                      <div className="flex items-center gap-2 text-sm text-emerald-600">
                        <Check className="w-4 h-4" />
                        {selectedProducts.size} ürün seçili
                      </div>
                    )}
                  </div>
                  <div className="flex gap-2">
                    {selectedProducts.size > 0 && (
                      <>
                        <Button 
                          variant="outline" 
                          onClick={clearSelection}
                          size="sm"
                        >
                          Seçimi Temizle
                        </Button>
                        <Button 
                          onClick={() => setShowCreateQuoteDialog(true)}
                          className="bg-blue-600 hover:bg-blue-700"
                          size="sm"
                        >
                          <FileText className="w-4 h-4 mr-2" />
                          Teklif Oluştur
                        </Button>
                      </>
                    )}
                    <Button 
                      variant="outline" 
                      onClick={selectAllVisible}
                      size="sm"
                    >
                      Tümünü Seç
                    </Button>
                  </div>
                  <Dialog open={showAddProductDialog} onOpenChange={setShowAddProductDialog}>
                    <DialogTrigger asChild>
                      <Button className="bg-emerald-600 hover:bg-emerald-700">
                        <Plus className="w-4 h-4 mr-2" />
                        Yeni Ürün Ekle
                      </Button>
                    </DialogTrigger>
                    <DialogContent className="max-w-md">
                      <DialogHeader>
                        <DialogTitle>Yeni Ürün Ekle</DialogTitle>
                        <DialogDescription>
                          Manuel olarak yeni bir ürün ekleyebilirsiniz
                        </DialogDescription>
                      </DialogHeader>
                      <div className="space-y-4">
                        <div>
                          <Label htmlFor="product-name">Ürün Adı</Label>
                          <Input
                            id="product-name"
                            placeholder="Ürün adını girin"
                            value={newProductForm.name}
                            onChange={(e) => setNewProductForm({...newProductForm, name: e.target.value})}
                          />
                        </div>
                        
                        <div>
                          <Label htmlFor="product-company">Firma</Label>
                          <Select 
                            value={newProductForm.company_id} 
                            onValueChange={(value) => setNewProductForm({...newProductForm, company_id: value})}
                          >
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
                          <Label htmlFor="product-category">Kategori (Opsiyonel)</Label>
                          <Select 
                            value={newProductForm.category_id || "none"} 
                            onValueChange={(value) => setNewProductForm({...newProductForm, category_id: value === "none" ? "" : value})}
                          >
                            <SelectTrigger>
                              <SelectValue placeholder="Kategori seçin" />
                            </SelectTrigger>
                            <SelectContent>
                              <SelectItem value="none">Kategorsiz</SelectItem>
                              {categories.map((category) => (
                                <SelectItem key={category.id} value={category.id}>
                                  <div className="flex items-center gap-2">
                                    <div 
                                      className="w-2 h-2 rounded-full" 
                                      style={{backgroundColor: category.color}}
                                    ></div>
                                    {category.name}
                                  </div>
                                </SelectItem>
                              ))}
                            </SelectContent>
                          </Select>
                        </div>

                        <div className="grid grid-cols-2 gap-4">
                          <div>
                            <Label htmlFor="product-price">Liste Fiyatı</Label>
                            <Input
                              id="product-price"
                              type="number"
                              step="0.01"
                              placeholder="0.00"
                              value={newProductForm.list_price}
                              onChange={(e) => setNewProductForm({...newProductForm, list_price: e.target.value})}
                            />
                          </div>
                          
                          <div>
                            <Label htmlFor="product-currency">Para Birimi</Label>
                            <Select 
                              value={newProductForm.currency} 
                              onValueChange={(value) => setNewProductForm({...newProductForm, currency: value})}
                            >
                              <SelectTrigger>
                                <SelectValue />
                              </SelectTrigger>
                              <SelectContent>
                                <SelectItem value="USD">USD ($)</SelectItem>
                                <SelectItem value="EUR">EUR (€)</SelectItem>
                                <SelectItem value="TRY">TRY (₺)</SelectItem>
                              </SelectContent>
                            </Select>
                          </div>
                        </div>

                        <div>
                          <Label htmlFor="product-discounted">İndirimli Fiyat (Opsiyonel)</Label>
                          <Input
                            id="product-discounted"
                            type="number"
                            step="0.01"
                            placeholder="0.00"
                            value={newProductForm.discounted_price}
                            onChange={(e) => setNewProductForm({...newProductForm, discounted_price: e.target.value})}
                          />
                        </div>

                        <div>
                          <Label htmlFor="product-description">Açıklama (Opsiyonel)</Label>
                          <Input
                            id="product-description"
                            placeholder="Ürün açıklaması"
                            value={newProductForm.description}
                            onChange={(e) => setNewProductForm({...newProductForm, description: e.target.value})}
                          />
                        </div>

                        <div>
                          <Label htmlFor="product-image">Görsel URL (Opsiyonel)</Label>
                          <Input
                            id="product-image"
                            type="url"
                            placeholder="https://example.com/image.jpg"
                            value={newProductForm.image_url}
                            onChange={(e) => setNewProductForm({...newProductForm, image_url: e.target.value})}
                          />
                        </div>
                      </div>
                      <DialogFooter>
                        <Button 
                          variant="outline" 
                          onClick={() => {
                            setShowAddProductDialog(false);
                            resetNewProductForm();
                          }}
                        >
                          İptal
                        </Button>
                        <Button 
                          onClick={createProduct}
                          disabled={loading}
                          className="bg-emerald-600 hover:bg-emerald-700"
                        >
                          {loading ? 'Ekleniyor...' : 'Ürün Ekle'}
                        </Button>
                      </DialogFooter>
                    </DialogContent>
                  </Dialog>
                </div>

                {/* Search and Filter Controls */}
                <div className="flex flex-col md:flex-row gap-4 mb-6">
                  <div className="flex-1">
                    <Input
                      placeholder="Ürün ara..."
                      value={searchQuery}
                      onChange={(e) => handleSearch(e.target.value)}
                      className="w-full"
                    />
                  </div>
                  <div className="flex gap-2">
                    <Select value={selectedCategory || "all"} onValueChange={handleCategoryFilter}>
                      <SelectTrigger className="w-48">
                        <SelectValue placeholder="Kategori seç" />
                      </SelectTrigger>
                      <SelectContent>
                        <SelectItem value="all">Tüm Kategoriler</SelectItem>
                        {categories.map((category) => (
                          <SelectItem key={category.id} value={category.id}>
                            {category.name}
                          </SelectItem>
                        ))}
                      </SelectContent>
                    </Select>
                    {(searchQuery || selectedCategory) && (
                      <Button 
                        variant="outline" 
                        onClick={() => {
                          handleSearch('');
                          handleCategoryFilter('');
                        }}
                      >
                        Temizle
                      </Button>
                    )}
                  </div>
                </div>
                <div className="space-y-8">
                  {(() => {
                    // Group products by category
                    const groupedProducts = {};
                    
                    products.forEach(product => {
                      const categoryId = product.category_id || 'uncategorized';
                      if (!groupedProducts[categoryId]) {
                        groupedProducts[categoryId] = [];
                      }
                      groupedProducts[categoryId].push(product);
                    });

                    // Sort categories: show categorized products first, then uncategorized
                    const sortedGroups = Object.entries(groupedProducts).sort(([a], [b]) => {
                      if (a === 'uncategorized') return 1;
                      if (b === 'uncategorized') return -1;
                      return 0;
                    });

                    return sortedGroups.map(([categoryId, categoryProducts]) => {
                      const category = categories.find(c => c.id === categoryId);
                      const categoryName = category ? category.name : 'Kategorsiz Ürünler';
                      const categoryColor = category ? category.color : '#64748b';

                      return (
                        <div key={categoryId} className="space-y-4">
                          {/* Category Header */}
                          <div className="flex items-center gap-3 pb-2 border-b-2" style={{borderColor: categoryColor}}>
                            <div 
                              className="w-4 h-4 rounded-full" 
                              style={{backgroundColor: categoryColor}}
                            ></div>
                            <h3 className="text-lg font-semibold text-slate-800">
                              {categoryName}
                            </h3>
                            <Badge variant="outline" className="ml-auto">
                              {categoryProducts.length} ürün
                            </Badge>
                          </div>

                          {/* Products Table for this category */}
                          <div className="overflow-x-auto">
                            <Table>
                              <TableHeader>
                                <TableRow>
                                  <TableHead className="w-12">
                                    <div className="flex items-center gap-2">
                                      <input
                                        type="checkbox"
                                        className="rounded border-gray-300"
                                        checked={categoryProducts.every(p => selectedProducts.has(p.id))}
                                        onChange={(e) => {
                                          if (e.target.checked) {
                                            const newSelected = new Map(selectedProducts);
                                            categoryProducts.forEach(p => newSelected.set(p.id, 1));
                                            setSelectedProducts(newSelected);
                                          } else {
                                            const newSelected = new Map(selectedProducts);
                                            categoryProducts.forEach(p => newSelected.delete(p.id));
                                            setSelectedProducts(newSelected);
                                          }
                                        }}
                                      />
                                      <span className="text-xs">Seç / Adet</span>
                                    </div>
                                  </TableHead>
                                  <TableHead>Ürün</TableHead>
                                  <TableHead>Firma</TableHead>
                                  <TableHead>Liste Fiyatı</TableHead>
                                  <TableHead>İndirimli Fiyat</TableHead>
                                  <TableHead>Para Birimi</TableHead>
                                  <TableHead>TL Fiyat</TableHead>
                                  <TableHead>TL İndirimli</TableHead>
                                  <TableHead>İşlemler</TableHead>
                                </TableRow>
                              </TableHeader>
                              <TableBody>
                                {categoryProducts.map((product) => {
                                  const company = companies.find(c => c.id === product.company_id);
                                  const isEditing = editingProduct === product.id;
                                  
                                  return (
                                    <TableRow 
                                      key={product.id}
                                      className={selectedProducts.has(product.id) ? 'bg-blue-50 border-blue-200' : ''}
                                    >
                                      <TableCell>
                                        <div className="flex items-center gap-2">
                                          <input
                                            type="checkbox"
                                            className="rounded border-gray-300"
                                            checked={selectedProducts.has(product.id)}
                                            onChange={(e) => {
                                              if (e.target.checked) {
                                                toggleProductSelection(product.id, 1);
                                              } else {
                                                toggleProductSelection(product.id, 0);
                                              }
                                            }}
                                          />
                                          {selectedProducts.has(product.id) && (
                                            <input
                                              type="number"
                                              min="1"
                                              value={selectedProducts.get(product.id) || 1}
                                              onChange={(e) => {
                                                const quantity = parseInt(e.target.value) || 1;
                                                toggleProductSelection(product.id, quantity);
                                              }}
                                              className="w-16 px-2 py-1 text-sm border rounded"
                                              placeholder="1"
                                            />
                                          )}
                                        </div>
                                      </TableCell>
                                      <TableCell className="font-medium">
                                        {isEditing ? (
                                          <div className="space-y-2">
                                            <Input
                                              value={editForm.name}
                                              onChange={(e) => setEditForm({...editForm, name: e.target.value})}
                                              className="min-w-[200px]"
                                              placeholder="Ürün adı"
                                            />
                                            <Input
                                              value={editForm.description}
                                              onChange={(e) => setEditForm({...editForm, description: e.target.value})}
                                              className="min-w-[200px]"
                                              placeholder="Açıklama (opsiyonel)"
                                            />
                                            <Input
                                              value={editForm.image_url}
                                              onChange={(e) => setEditForm({...editForm, image_url: e.target.value})}
                                              className="min-w-[200px]"
                                              placeholder="Görsel URL (opsiyonel)"
                                              type="url"
                                            />
                                            <Select 
                                              value={editForm.category_id || "none"} 
                                              onValueChange={(value) => setEditForm({...editForm, category_id: value === "none" ? "" : value})}
                                            >
                                              <SelectTrigger className="min-w-[200px]">
                                                <SelectValue placeholder="Kategori" />
                                              </SelectTrigger>
                                              <SelectContent>
                                                <SelectItem value="none">Kategorsiz</SelectItem>
                                                {categories.map((category) => (
                                                  <SelectItem key={category.id} value={category.id}>
                                                    {category.name}
                                                  </SelectItem>
                                                ))}
                                              </SelectContent>
                                            </Select>
                                          </div>
                                        ) : (
                                          <div className="space-y-1">
                                            <div className="flex items-start gap-3">
                                              {product.image_url && (
                                                <img 
                                                  src={product.image_url} 
                                                  alt={product.name}
                                                  className="w-12 h-12 object-cover rounded border"
                                                  onError={(e) => {e.target.style.display = 'none'}}
                                                />
                                              )}
                                              <div>
                                                <div className="font-medium">{product.name}</div>
                                                {product.description && (
                                                  <div className="text-sm text-slate-500 mt-1">{product.description}</div>
                                                )}
                                              </div>
                                            </div>
                                          </div>
                                        )}
                                      </TableCell>
                                      <TableCell>
                                        <Badge variant="outline">{company?.name || 'Unknown'}</Badge>
                                      </TableCell>
                                      <TableCell>
                                        {isEditing ? (
                                          <Input
                                            type="number"
                                            step="0.01"
                                            value={editForm.list_price}
                                            onChange={(e) => setEditForm({...editForm, list_price: e.target.value})}
                                            className="w-24"
                                          />
                                        ) : (
                                          `${getCurrencySymbol(product.currency)} ${formatPrice(product.list_price)}`
                                        )}
                                      </TableCell>
                                      <TableCell>
                                        {isEditing ? (
                                          <Input
                                            type="number"
                                            step="0.01"
                                            value={editForm.discounted_price}
                                            onChange={(e) => setEditForm({...editForm, discounted_price: e.target.value})}
                                            className="w-24"
                                            placeholder="İndirimli fiyat"
                                          />
                                        ) : (
                                          product.discounted_price ? (
                                            `${getCurrencySymbol(product.currency)} ${formatPrice(product.discounted_price)}`
                                          ) : '-'
                                        )}
                                      </TableCell>
                                      <TableCell>
                                        {isEditing ? (
                                          <Select 
                                            value={editForm.currency} 
                                            onValueChange={(value) => setEditForm({...editForm, currency: value})}
                                          >
                                            <SelectTrigger className="w-20">
                                              <SelectValue />
                                            </SelectTrigger>
                                            <SelectContent>
                                              <SelectItem value="USD">USD</SelectItem>
                                              <SelectItem value="EUR">EUR</SelectItem>
                                              <SelectItem value="TRY">TRY</SelectItem>
                                            </SelectContent>
                                          </Select>
                                        ) : (
                                          <Badge 
                                            className="cursor-pointer hover:bg-primary/90" 
                                            onClick={() => startEditProduct(product)}
                                          >
                                            {product.currency}
                                          </Badge>
                                        )}
                                      </TableCell>
                                      <TableCell>
                                        ₺ {product.list_price_try ? formatPrice(product.list_price_try) : '---'}
                                      </TableCell>
                                      <TableCell>
                                        {product.discounted_price_try ? (
                                          `₺ ${formatPrice(product.discounted_price_try)}`
                                        ) : '-'}
                                      </TableCell>
                                      <TableCell>
                                        <div className="flex gap-2">
                                          {isEditing ? (
                                            <>
                                              <Button 
                                                size="sm" 
                                                onClick={saveEditProduct}
                                                disabled={loading}
                                                className="bg-green-600 hover:bg-green-700"
                                              >
                                                <Save className="w-4 h-4" />
                                              </Button>
                                              <Button 
                                                size="sm" 
                                                variant="outline" 
                                                onClick={cancelEditProduct}
                                              >
                                                <X className="w-4 h-4" />
                                              </Button>
                                            </>
                                          ) : (
                                            <>
                                              <Button 
                                                size="sm" 
                                                variant="outline" 
                                                onClick={() => startEditProduct(product)}
                                              >
                                                <Edit className="w-4 h-4" />
                                              </Button>
                                              <Button 
                                                size="sm" 
                                                variant="destructive" 
                                                onClick={() => deleteProduct(product.id)}
                                              >
                                                <Trash2 className="w-4 h-4" />
                                              </Button>
                                            </>
                                          )}
                                        </div>
                                      </TableCell>
                                    </TableRow>
                                  );
                                })}
                              </TableBody>
                            </Table>
                          </div>
                        </div>
                      );
                    });
                  })()}
                </div>
              </CardContent>
            </Card>
          </TabsContent>

          {/* Quotes Tab */}
          <TabsContent value="quotes" className="space-y-6">
            <Card>
              <CardHeader>
                <CardTitle className="flex items-center gap-2">
                  <FileText className="w-5 h-5" />
                  Teklif Yönetimi
                </CardTitle>
                <CardDescription>Seçili ürünlerden teklif oluşturun ve yönetin</CardDescription>
              </CardHeader>
              <CardContent>
                {selectedProducts.size > 0 ? (
                  <div className="space-y-6">
                    {/* Selected Products Summary */}
                    <div className="bg-blue-50 border border-blue-200 rounded-lg p-4">
                      <h4 className="font-semibold text-blue-900 mb-2">
                        Seçili Ürünler ({selectedProducts.size} çeşit, {calculateQuoteTotals().totalQuantity} adet)
                      </h4>
                      <div className="grid gap-2">
                        {getSelectedProductsData().slice(0, 5).map((product) => {
                          const company = companies.find(c => c.id === product.company_id);
                          return (
                            <div key={product.id} className="flex items-center justify-between bg-white rounded p-2 text-sm">
                              <div className="flex items-center gap-3">
                                {product.image_url && (
                                  <img 
                                    src={product.image_url} 
                                    alt={product.name}
                                    className="w-8 h-8 object-cover rounded"
                                    onError={(e) => {e.target.style.display = 'none'}}
                                  />
                                )}
                                <div>
                                  <div className="font-medium">{product.name}</div>
                                  <div className="text-slate-500 text-xs">{company?.name}</div>
                                </div>
                              </div>
                              <div className="flex items-center gap-3">
                                <div className="flex items-center gap-2">
                                  <span className="text-xs text-slate-600">Adet:</span>
                                  <input
                                    type="number"
                                    min="1"
                                    value={product.quantity || 1}
                                    onChange={(e) => {
                                      const quantity = parseInt(e.target.value) || 1;
                                      toggleProductSelection(product.id, quantity);
                                    }}
                                    className="w-16 px-2 py-1 text-sm border rounded"
                                  />
                                </div>
                                <div className="text-right">
                                  <div className="font-medium">₺ {formatPrice((product.list_price_try || 0) * (product.quantity || 1))}</div>
                                  <div className="text-xs text-slate-500">
                                    ₺ {formatPrice(product.list_price_try || 0)} × {product.quantity || 1}
                                  </div>
                                </div>
                                <Button
                                  variant="ghost"
                                  size="sm"
                                  onClick={() => toggleProductSelection(product.id, 0)}
                                  className="text-red-600 hover:text-red-800 hover:bg-red-50"
                                >
                                  <X className="w-4 h-4" />
                                </Button>
                              </div>
                            </div>
                          );
                        })}
                        {selectedProducts.size > 5 && (
                          <div className="text-center text-sm text-slate-500 py-2">
                            ... ve {selectedProducts.size - 5} ürün daha
                          </div>
                        )}
                      </div>
                    </div>

                    {/* Manual Discount Control */}
                    <div className="bg-amber-50 border border-amber-200 rounded-lg p-4">
                      <h4 className="font-semibold text-amber-900 mb-3">İndirim Uygula</h4>
                      <div className="flex items-center gap-4">
                        <Label htmlFor="discount-input" className="font-medium">İndirim Yüzdesi:</Label>
                        <div className="flex items-center gap-2">
                          <Input
                            id="discount-input"
                            type="number"
                            min="0"
                            max="100"
                            step="0.1"
                            value={quoteDiscount}
                            onChange={(e) => setQuoteDiscount(parseFloat(e.target.value) || 0)}
                            className="w-20"
                          />
                          <span className="text-amber-700">%</span>
                        </div>
                        <div className="flex gap-2 ml-auto">
                          <Button
                            variant="outline"
                            size="sm"
                            onClick={() => setQuoteDiscount(5)}
                          >
                            5%
                          </Button>
                          <Button
                            variant="outline"
                            size="sm"
                            onClick={() => setQuoteDiscount(10)}
                          >
                            10%
                          </Button>
                          <Button
                            variant="outline"
                            size="sm"
                            onClick={() => setQuoteDiscount(15)}
                          >
                            15%
                          </Button>
                          <Button
                            variant="outline"
                            size="sm"
                            onClick={() => setQuoteDiscount(20)}
                          >
                            20%
                          </Button>
                        </div>
                      </div>
                    </div>

                    {/* İşçilik Maliyeti Bölümü */}
                    <div className="bg-green-50 border border-green-200 rounded-lg p-4">
                      <div className="flex items-center justify-between">
                        <div className="flex items-center gap-2">
                          <Wrench className="w-4 h-4 text-green-600" />
                          <span className="font-medium text-green-900">İşçilik Maliyeti</span>
                        </div>
                        <div className="flex items-center gap-2">
                          <span className="text-green-700">₺</span>
                          <Input
                            type="number"
                            min="0"
                            step="0.01"
                            placeholder="0.00"
                            value={quoteLaborCost}
                            onChange={(e) => setQuoteLaborCost(parseFloat(e.target.value) || 0)}
                            className="w-32"
                          />
                        </div>
                        <div className="flex gap-2 ml-auto">
                          <Button
                            variant="outline"
                            size="sm"
                            onClick={() => setQuoteLaborCost(500)}
                          >
                            ₺500
                          </Button>
                          <Button
                            variant="outline"
                            size="sm"
                            onClick={() => setQuoteLaborCost(1000)}
                          >
                            ₺1000
                          </Button>
                          <Button
                            variant="outline"
                            size="sm"
                            onClick={() => setQuoteLaborCost(1500)}
                          >
                            ₺1500
                          </Button>
                          <Button
                            variant="outline"
                            size="sm"
                            onClick={() => setQuoteLaborCost(2000)}
                          >
                            ₺2000
                          </Button>
                        </div>
                      </div>
                    </div>

                    {/* Quote Summary */}
                    <div className="bg-emerald-50 border border-emerald-200 rounded-lg p-4">
                      <h4 className="font-semibold text-emerald-900 mb-3">Teklif Özeti</h4>
                      <div className="grid grid-cols-2 md:grid-cols-4 gap-4">
                        <div className="text-center">
                          <div className="text-2xl font-bold text-emerald-800">
                            {calculateQuoteTotals().productCount}
                          </div>
                          <div className="text-sm text-emerald-600">Ürün Sayısı</div>
                        </div>
                        <div className="text-center">
                          <div className="text-2xl font-bold text-emerald-800">
                            ₺ {formatPrice(calculateQuoteTotals().totalListPrice)}
                          </div>
                          <div className="text-sm text-emerald-600">Toplam Liste Fiyatı</div>
                        </div>
                        <div className="text-center">
                          <div className="text-2xl font-bold text-red-600">
                            - ₺ {formatPrice(calculateQuoteTotals().discountAmount)}
                          </div>
                          <div className="text-sm text-red-500">İndirim ({quoteDiscount}%)</div>
                        </div>
                        <div className="text-center">
                          <div className="text-2xl font-bold text-emerald-800">
                            ₺ {formatPrice(calculateQuoteTotals().totalNetPrice)}
                          </div>
                          <div className="text-sm text-emerald-600">Net Toplam</div>
                        </div>
                      </div>
                      
                      {quoteDiscount > 0 && (
                        <div className="mt-4 p-3 bg-white rounded border border-emerald-300">
                          <div className="text-sm text-emerald-700">
                            <strong>İndirim Detayları:</strong> Liste fiyatı üzerinden %{quoteDiscount} indirim uygulandı.
                            Tasarruf tutarı: <strong>₺ {formatPrice(calculateQuoteTotals().discountAmount)}</strong>
                          </div>
                        </div>
                      )}
                    </div>

                    {/* Action Buttons */}
                    <div className="flex gap-4">
                      <Button 
                        onClick={() => setShowCreateQuoteDialog(true)}
                        className="bg-blue-600 hover:bg-blue-700 flex-1"
                      >
                        <FileText className="w-4 h-4 mr-2" />
                        Resmi Teklif Oluştur
                      </Button>
                      <Button 
                        variant="outline" 
                        onClick={() => {
                          const csvContent = getSelectedProductsData().map(p => {
                            const company = companies.find(c => c.id === p.company_id);
                            const listPrice = p.list_price_try || 0;
                            const netPrice = listPrice * (1 - quoteDiscount / 100);
                            return `"${p.name}","${company?.name || 'Unknown'}","₺ ${formatPrice(listPrice)}","₺ ${formatPrice(netPrice)}","%${quoteDiscount}"`;
                          }).join('\n');
                          const header = `"Ürün Adı","Firma","Liste Fiyatı","Net Fiyat","İndirim"\n`;
                          const totalRow = `\n"TOPLAM","","₺ ${formatPrice(calculateQuoteTotals().totalListPrice)}","₺ ${formatPrice(calculateQuoteTotals().totalNetPrice)}","₺ ${formatPrice(calculateQuoteTotals().discountAmount)}"`;
                          const blob = new Blob([header + csvContent + totalRow], { type: 'text/csv' });
                          const url = URL.createObjectURL(blob);
                          const a = document.createElement('a');
                          a.href = url;
                          a.download = `teklif_${new Date().toLocaleDateString('tr-TR').replace(/\./g, '_')}.csv`;
                          a.click();
                        }}
                      >
                        CSV İndir
                      </Button>
                      <Button 
                        variant="outline" 
                        onClick={clearSelection}
                      >
                        Seçimi Temizle
                      </Button>
                    </div>
                  </div>
                ) : (
                  <div className="text-center py-12 text-slate-500">
                    <FileText className="w-16 h-16 mx-auto mb-4 opacity-50" />
                    <h3 className="text-lg font-semibold mb-2">Henüz Ürün Seçilmedi</h3>
                    <p className="text-sm mb-4">
                      Teklif oluşturmak için önce "Ürünler" sekmesinden ürün seçin
                    </p>
                    <Button 
                      variant="outline"
                      onClick={() => {
                        // Switch to products tab
                        const productsTab = document.querySelector('[role="tab"][value="products"]');
                        if (productsTab) productsTab.click();
                      }}
                    >
                      Ürünlere Git
                    </Button>
                  </div>
                )}
                
                {/* Kayıtlı Teklifler Bölümü */}
                {quotes.length > 0 && (
                  <Card className="mt-8">
                    <CardHeader>
                      <CardTitle className="flex items-center gap-2">
                        <Archive className="w-5 h-5" />
                        Kayıtlı Teklifler
                      </CardTitle>
                      <CardDescription>
                        Daha önce oluşturduğunuz {quotes.length} teklif
                        {filteredQuotes.length !== quotes.length && ` (${filteredQuotes.length} sonuç gösteriliyor)`}
                      </CardDescription>
                      
                      {/* Teklif Arama */}
                      <div className="mt-4">
                        <Input
                          placeholder="Teklif adı, müşteri adı veya ürün adı ile ara..."
                          value={quoteSearchTerm}
                          onChange={(e) => handleQuoteSearch(e.target.value)}
                          className="max-w-md"
                        />
                      </div>
                    </CardHeader>
                    <CardContent>
                      {filteredQuotes.length === 0 ? (
                        <div className="text-center py-8 text-slate-500">
                          <FileText className="w-12 h-12 mx-auto mb-3 opacity-50" />
                          <p>"{quoteSearchTerm}" araması için sonuç bulunamadı</p>
                          <Button 
                            variant="outline" 
                            size="sm" 
                            className="mt-2"
                            onClick={() => handleQuoteSearch('')}
                          >
                            Aramayı Temizle
                          </Button>
                        </div>
                      ) : (
                        <div className="space-y-4">
                          {filteredQuotes.map((quote) => (
                          <div key={quote.id} className="border rounded-lg p-4 hover:bg-slate-50">
                            <div className="flex justify-between items-start">
                              <div className="flex-1">
                                <h4 className="font-semibold text-lg">{quote.name}</h4>
                                <p className="text-sm text-slate-600 mt-1">
                                  {quote.products.length} ürün • %{quote.discount_percentage} indirim
                                </p>
                                <div className="flex items-center gap-4 mt-2 text-sm text-slate-600">
                                  <span>Ara Toplam: ₺{formatPrice(quote.total_discounted_price)}</span>
                                  <span>Net Toplam: ₺{formatPrice(quote.total_net_price)}</span>
                                  <span>{new Date(quote.created_at).toLocaleDateString('tr-TR')}</span>
                                </div>
                              </div>
                              <div className="flex gap-2">
                                <Button
                                  variant="outline"
                                  size="sm"
                                  onClick={() => {
                                    // Teklifin ürünlerini seç
                                    const productIds = new Map();
                                    quote.products.forEach(p => productIds.set(p.id, 1));
                                    setSelectedProducts(productIds);
                                    setQuoteDiscount(quote.discount_percentage);
                                    toast.success(`"${quote.name}" teklifi yüklendi`);
                                  }}
                                >
                                  Yükle
                                </Button>
                                <Button
                                  variant="default"
                                  size="sm"
                                  onClick={() => {
                                    // PDF indir
                                    const pdfUrl = `${API}/quotes/${quote.id}/pdf`;
                                    const link = document.createElement('a');
                                    link.href = pdfUrl;
                                    link.download = `${quote.name}.pdf`;
                                    document.body.appendChild(link);
                                    link.click();
                                    document.body.removeChild(link);
                                    toast.success('PDF indiriliyor...');
                                  }}
                                  className="bg-green-600 hover:bg-green-700"
                                >
                                  <Download className="w-4 h-4 mr-1" />
                                  PDF İndir
                                </Button>
                                <Button
                                  variant="destructive"
                                  size="sm"
                                  onClick={async () => {
                                    if (window.confirm(`"${quote.name}" teklifini silmek istediğinizden emin misiniz?`)) {
                                      try {
                                        const response = await fetch(`${API}/quotes/${quote.id}`, {
                                          method: 'DELETE'
                                        });
                                        
                                        if (response.ok) {
                                          await fetchQuotes();
                                          toast.success('Teklif silindi');
                                        } else {
                                          throw new Error('Silme işlemi başarısız');
                                        }
                                      } catch (error) {
                                        toast.error('Teklif silinemedi');
                                      }
                                    }
                                  }}
                                >
                                  Sil
                                </Button>
                              </div>
                            </div>
                            
                            {/* Teklif detayları açılır bölüm */}
                            <details className="mt-3">
                              <summary className="cursor-pointer text-sm text-blue-600 hover:text-blue-800">
                                Ürünleri Göster ({quote.products.length} ürün)
                              </summary>
                              <div className="mt-2 space-y-2">
                                {quote.products.map((product, index) => (
                                  <div key={index} className="flex justify-between items-center py-1 px-2 bg-slate-50 rounded text-sm">
                                    <span>{product.name}</span>
                                    <span className="text-slate-600">
                                      ₺{formatPrice(product.discounted_price_try || product.list_price_try)}
                                    </span>
                                  </div>
                                ))}
                              </div>
                            </details>
                          </div>
                        ))}
                        </div>
                      )}
                    </CardContent>
                  </Card>
                )}
              </CardContent>
            </Card>
          </TabsContent>

        </Tabs>
      </div>

      {/* Create Quote Dialog */}
      <Dialog open={showCreateQuoteDialog} onOpenChange={setShowCreateQuoteDialog}>
        <DialogContent className="max-w-2xl">
          <DialogHeader>
            <DialogTitle>Resmi Teklif Oluştur</DialogTitle>
            <DialogDescription>
              Seçili {selectedProducts.size} ürün için profesyonel teklif hazırlayın
            </DialogDescription>
          </DialogHeader>
          <div className="space-y-4">
            <div>
              <Label htmlFor="quote-name">Teklif Adı</Label>
              <Input
                id="quote-name"
                placeholder="Örn: Solar Panel Sistemi Teklifi"
                value={quoteName}
                onChange={(e) => setQuoteName(e.target.value)}
              />
            </div>
            
            {/* Quote Preview */}
            <div className="bg-slate-50 rounded-lg p-4 max-h-60 overflow-y-auto">
              <h4 className="font-semibold mb-3">Teklif Özeti</h4>
              <div className="space-y-2 text-sm">
                {getSelectedProductsData().map((product, index) => {
                  const company = companies.find(c => c.id === product.company_id);
                  return (
                    <div key={product.id} className="flex justify-between items-center py-1 border-b border-slate-200">
                      <div className="flex-1">
                        <span className="font-medium">{index + 1}. {product.name}</span>
                        <span className="text-slate-500 ml-2">({company?.name})</span>
                      </div>
                      <div className="text-right">
                        <div className="space-y-1">
                          <div className="text-slate-500 text-xs">Liste: ₺ {formatPrice(product.list_price_try)}</div>
                          <div className="font-medium">
                            ₺ {formatPrice((product.list_price_try || 0) * (1 - quoteDiscount / 100))}
                          </div>
                        </div>
                      </div>
                    </div>
                  );
                })}
                <div className="space-y-1 pt-2 border-t-2 border-slate-300">
                  <div className="flex justify-between items-center text-sm text-slate-600">
                    <span>Ara Toplam:</span>
                    <span>₺ {formatPrice(calculateQuoteTotals().totalListPrice)}</span>
                  </div>
                  {quoteDiscount > 0 && (
                    <div className="flex justify-between items-center text-sm text-red-600">
                      <span>İndirim (%{quoteDiscount}):</span>
                      <span>- ₺ {formatPrice(calculateQuoteTotals().discountAmount)}</span>
                    </div>
                  )}
                  <div className="flex justify-between items-center font-bold text-lg">
                    <span>NET TOPLAM:</span>
                    <span>₺ {formatPrice(calculateQuoteTotals().totalNetPrice)}</span>
                  </div>
                </div>
              </div>
            </div>
          </div>
          <DialogFooter>
            <Button 
              variant="outline" 
              onClick={() => {
                setShowCreateQuoteDialog(false);
                setQuoteName('');
              }}
            >
              İptal
            </Button>
            <Button 
              onClick={async () => {
                try {
                  // Backend'e teklif kaydet
                  const quoteTotals = calculateQuoteTotals();
                  const selectedProductData = getSelectedProductsData().map(p => ({
                    id: p.id,
                    quantity: p.quantity || 1
                  }));
                  
                  const quoteData = {
                    name: quoteName || `Teklif ${new Date().toLocaleDateString('tr-TR')}`,
                    discount_percentage: parseFloat(quoteDiscount) || 0,
                    products: selectedProductData,
                    notes: null
                  };
                  
                  const response = await fetch(`${API}/quotes`, {
                    method: 'POST',
                    headers: {
                      'Content-Type': 'application/json',
                    },
                    body: JSON.stringify(quoteData)
                  });
                  
                  if (!response.ok) {
                    throw new Error('Teklif kaydedilemedi');
                  }
                  
                  const savedQuote = await response.json();
                  
                  // Teklifleri yeniden yükle
                  await fetchQuotes();
                  
                  // Dialog'u kapat ve formu temizle
                  setShowCreateQuoteDialog(false);
                  setQuoteName('');
                  setQuoteDiscount(0);
                  
                  toast.success(`"${savedQuote.name}" teklifi başarıyla kaydedildi`);
                  
                } catch (error) {
                  console.error('Teklif kaydetme hatası:', error);
                  toast.error('Teklif kaydedilemedi: ' + error.message);
                }
              }}
              className="bg-blue-600 hover:bg-blue-700"
              disabled={!quoteName.trim()}
            >
              <FileText className="w-4 h-4 mr-2" />
              Teklif Oluştur
            </Button>
          </DialogFooter>
        </DialogContent>
      </Dialog>

      <Toaster position="top-right" />
    </div>
  );
}

export default App;