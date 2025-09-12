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
import { Trash2, Upload, RefreshCw, Plus, TrendingUp, Building2, Package, DollarSign, Edit, Save, X, FileText, Check, Archive, Download, Wrench, Eye, EyeOff, AlertTriangle, Tags } from 'lucide-react';
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
  const [uploadCompanyName, setUploadCompanyName] = useState(''); // Excel yükleme için manuel firma adı
  const [useExistingCompany, setUseExistingCompany] = useState(true); // Mevcut firma mı yoksa yeni mi
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
  const [quoteDiscount, setQuoteDiscount] = useState(0);
  const [quoteLaborCost, setQuoteLaborCost] = useState(0); // İşçilik maliyeti state'i
  const [loadedQuote, setLoadedQuote] = useState(null); // Yüklenen teklif bilgisi
  const [showDiscountedPrices, setShowDiscountedPrices] = useState(false); // İndirimli fiyat görünürlüğü - Varsayılan KAPALI
  const [showQuoteDiscountedPrices, setShowQuoteDiscountedPrices] = useState(false); // Teklif indirimli fiyat görünürlüğü - Varsayılan KAPALI
  
  // Kategori ürün atama için state'ler
  const [showCategoryProductDialog, setShowCategoryProductDialog] = useState(false);
  const [selectedCategoryForProducts, setSelectedCategoryForProducts] = useState(null);
  const [uncategorizedProducts, setUncategorizedProducts] = useState([]);
  const [selectedProductsForCategory, setSelectedProductsForCategory] = useState(new Set());
  
  // Ürünler sekmesinden teklif oluşturma için state'ler
  const [showQuickQuoteDialog, setShowQuickQuoteDialog] = useState(false);
  const [quickQuoteCustomerName, setQuickQuoteCustomerName] = useState('');
  const [activeTab, setActiveTab] = useState('products');
  const [quotes, setQuotes] = useState([]);
  const [selectedQuote, setSelectedQuote] = useState(null);
  const [quoteSearchTerm, setQuoteSearchTerm] = useState('');
  const [filteredQuotes, setFilteredQuotes] = useState([]);
  
  // Upload History için state'ler
  const [showUploadHistoryDialog, setShowUploadHistoryDialog] = useState(false);
  const [selectedCompanyForHistory, setSelectedCompanyForHistory] = useState(null);
  const [uploadHistory, setUploadHistory] = useState([]);
  const [loadingHistory, setLoadingHistory] = useState(false);
  
  // Para birimi değiştirme için state'ler
  const [showCurrencyChangeDialog, setShowCurrencyChangeDialog] = useState(false);
  const [selectedUploadForCurrency, setSelectedUploadForCurrency] = useState(null);
  const [newCurrency, setNewCurrency] = useState('USD');
  const [changingCurrency, setChangingCurrency] = useState(false);
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

  // Pagination ve performance için state'ler
  const [currentPage, setCurrentPage] = useState(1);
  const [totalProducts, setTotalProducts] = useState(0);
  const [productsPerPage] = useState(50); // Sayfa başına ürün sayısı
  const [loadingProducts, setLoadingProducts] = useState(false);

  // Kategori renk paleti sistemi
  const categoryColorPalette = [
    '#3B82F6', // Mavi
    '#10B981', // Yeşil
    '#F59E0B', // Turuncu
    '#EF4444', // Kırmızı
    '#8B5CF6', // Mor
    '#06B6D4', // Cyan
    '#84CC16', // Lime
    '#F97316', // Orange
    '#EC4899', // Pink
    '#6366F1', // Indigo
    '#14B8A6', // Teal
    '#F43F5E', // Rose
    '#A855F7', // Violet
    '#22D3EE', // Sky
    '#65A30D'  // Green-600
  ];

  // Bir sonraki rengi otomatik seç
  const getNextCategoryColor = () => {
    const usedColors = categories.map(cat => cat.color).filter(Boolean);
    const availableColors = categoryColorPalette.filter(color => !usedColors.includes(color));
    
    // Eğer tüm renkler kullanıldıysa, en baştan başla
    if (availableColors.length === 0) {
      return categoryColorPalette[0];
    }
    
    return availableColors[0];
  };

  // Load initial data
  useEffect(() => {
    loadInitialData();
    
    // Döviz kurlarını her 30 dakikada bir sessizce güncelle
    const exchangeRateInterval = setInterval(() => {
      loadExchangeRates(false, false); // Sessiz güncelleme, toast yok
    }, 30 * 60 * 1000); // 30 dakika

    // Cleanup function
    return () => {
      clearInterval(exchangeRateInterval);
    };
  }, []);

  const loadInitialData = async () => {
    setLoading(true);
    try {
      await Promise.all([
        loadCompanies(),
        loadProducts(1, true),
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

  const loadProducts = async (page = 1, resetPage = false) => {
    try {
      setLoadingProducts(true);
      
      // If we're resetting page (due to search/filter), start from page 1
      if (resetPage) {
        page = 1;
        setCurrentPage(1);
      }
      
      const params = new URLSearchParams();
      if (searchQuery) params.append('search', searchQuery);
      if (selectedCategory) params.append('category_id', selectedCategory);
      params.append('page', page.toString());
      params.append('limit', productsPerPage.toString());
      
      // Get products and count simultaneously
      const [productsResponse, countResponse] = await Promise.all([
        axios.get(`${API}/products?${params.toString()}`),
        axios.get(`${API}/products/count?${params.toString().replace(/page=\d+&?/, '').replace(/limit=\d+&?/, '')}`)
      ]);
      
      const newProducts = productsResponse.data;
      const totalCount = countResponse.data.count;
      
      // If it's the first page or a reset, replace products
      if (page === 1 || resetPage) {
        setProducts(newProducts);
      } else {
        // If it's a subsequent page, append products
        setProducts(prev => [...prev, ...newProducts]);
      }
      
      setTotalProducts(totalCount);
      setCurrentPage(page);
      setStats(prev => ({ ...prev, totalProducts: totalCount }));
      
    } catch (error) {
      console.error('Error loading products:', error);
      toast.error('Ürünler yüklenemedi');
    } finally {
      setLoadingProducts(false);
    }
  };

  const loadCategories = async () => {
    try {
      const response = await axios.get(`${API}/categories`);
      setCategories(response.data);
      
      // Kategoriler yüklendikten sonra, bir sonraki rengi otomatik seç
      setTimeout(() => {
        const nextColor = getNextCategoryColor();
        setNewCategoryColor(nextColor);
      }, 100); // Küçük delay ile state güncellenene kadar bekle
      
    } catch (error) {
      console.error('Error loading categories:', error);
      toast.error('Kategoriler yüklenemedi');
    }
  };



  const loadExchangeRates = async (forceUpdate = false, showToast = true) => {
    try {
      let response;
      
      if (forceUpdate) {
        // Force update from API
        response = await axios.post(`${API}/exchange-rates/update`);
        if (response.data.success) {
          setExchangeRates(response.data.rates);
          if (showToast) {
            toast.success(response.data.message);
          }
          return true;
        }
      } else {
        // Regular load
        response = await axios.get(`${API}/exchange-rates`);
        if (response.data.success) {
          setExchangeRates(response.data.rates);
          return true;
        }
      }
    } catch (error) {
      console.error('Error loading exchange rates:', error);
      if (showToast) {
        if (forceUpdate) {
          toast.error('Döviz kurları güncellenemedi');
        } else {
          toast.error('Döviz kurları yüklenemedi');
        }
      }
      return false;
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
      await loadProducts(1, true);
      toast.success('Firma silindi');
    } catch (error) {
      console.error('Error deleting company:', error);
      toast.error('Firma silinemedi');
    }
  };

  const uploadExcelFile = async () => {
    let companyId = null;
    let companyName = '';

    // Mevcut firma seçildiyse
    if (useExistingCompany) {
      if (!selectedCompany) {
        toast.error('Lütfen bir firma seçin');
        return;
      }
      companyId = selectedCompany;
    } else {
      // Yeni firma adı girildiyse
      if (!uploadCompanyName.trim()) {
        toast.error('Lütfen firma adını girin');
        return;
      }
      companyName = uploadCompanyName.trim();
    }

    if (!uploadFile) {
      toast.error('Lütfen bir dosya seçin');
      return;
    }

    try {
      setLoading(true);

      // Eğer yeni firma adı girildiyse, önce firmayı oluştur
      if (!useExistingCompany) {
        const companyResponse = await axios.post(`${API}/companies`, { name: companyName });
        companyId = companyResponse.data.id;
        toast.success(`"${companyName}" firması oluşturuldu`);
        // Firma listesini güncelle
        await loadCompanies();
      }

      // Excel dosyasını yükle
      const formData = new FormData();
      formData.append('file', uploadFile);

      const response = await axios.post(`${API}/companies/${companyId}/upload-excel`, formData, {
        headers: { 'Content-Type': 'multipart/form-data' }
      });
      
      // Form alanlarını temizle
      setUploadFile(null);
      setSelectedCompany('');
      setUploadCompanyName('');
      await loadProducts(1, true);
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
      
      // Döviz kurlarını güncelle
      const exchangeSuccess = await loadExchangeRates(true);
      
      if (exchangeSuccess) {
        // Ürünleri de yeniden yükle (güncel kurlarla fiyat hesaplaması için)
        await loadProducts(1, true);
        toast.success('Döviz kurları başarıyla güncellendi!');
      }
    } catch (error) {
      console.error('Error refreshing exchange rates:', error);
      toast.error('Döviz kurları güncellenemedi');
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
      
      // Kategorileri yeniden yükle
      await loadCategories();
      
      // Delay ile next color seçimi (kategoriler state'i güncellenene kadar bekle)
      setTimeout(() => {
        const nextColor = getNextCategoryColor();
        setNewCategoryColor(nextColor);
      }, 200); // Biraz daha uzun delay
      
      toast.success('Kategori başarıyla oluşturuldu');
    } catch (error) {
      console.error('Error creating category:', error);
      toast.error('Kategori oluşturulamadı');
    }
  };

  const deleteCategory = async (categoryId) => {
    if (!window.confirm('Bu kategoriyi silmek istediğinizden emin misiniz? Kategorideki ürünler kategorisiz kalacak.')) {
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
      loadProducts(1, true); // Reset to page 1 when searching/filtering
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
    setQuoteDiscount(0);
    setQuoteLaborCost(0); // İşçilik maliyetini de temizle
    setLoadedQuote(null); // Yüklenen teklifi de temizle
    setQuoteName(''); // Teklif adını da temizle
  };

  // Kategorisi olmayan ürünleri getir
  const getUncategorizedProducts = () => {
    return products.filter(product => !product.category_id || product.category_id === 'none');
  };

  // Kategori ürün atama dialog'unu aç
  const openCategoryProductDialog = (category) => {
    setSelectedCategoryForProducts(category);
    setUncategorizedProducts(getUncategorizedProducts());
    setSelectedProductsForCategory(new Set());
    setShowCategoryProductDialog(true);
  };

  // Seçili ürünleri kategoriye ata
  const assignProductsToCategory = async () => {
    try {
      const productIds = Array.from(selectedProductsForCategory);
      
      // Her ürün için kategori güncelleme isteği gönder
      const updatePromises = productIds.map(async (productId) => {
        const response = await fetch(`${API}/products/${productId}`, {
          method: 'PUT',
          headers: {
            'Content-Type': 'application/json',
          },
          body: JSON.stringify({
            category_id: selectedCategoryForProducts.id
          })
        });
        
        if (!response.ok) {
          const errorText = await response.text();
          throw new Error(`Ürün ${productId} güncellenemedi: ${errorText}`);
        }
        
        return await response.json();
      });

      const results = await Promise.all(updatePromises);
      console.log('Güncelleme sonuçları:', results);
      
      // Ürünleri yeniden yükle
      await loadProducts();
      
      // Dialog'u kapat
      setShowCategoryProductDialog(false);
      setSelectedProductsForCategory(new Set());
      
      toast.success(`${productIds.length} ürün "${selectedCategoryForProducts.name}" kategorisine eklendi!`);
      
    } catch (error) {
      console.error('Ürün kategori atama hatası:', error);
      toast.error('Ürünler kategoriye eklenemedi: ' + error.message);
    }
  };

  // Ürünler sekmesinden hızlı teklif oluştur
  const createQuickQuote = async () => {
    try {
      if (!quickQuoteCustomerName.trim()) {
        toast.error('Lütfen müşteri adını girin');
        return;
      }

      const selectedProductData = getSelectedProductsData().map(p => ({
        id: p.id,
        quantity: p.quantity || 1
      }));

      const quoteData = {
        name: quickQuoteCustomerName.trim(),
        customer_name: quickQuoteCustomerName.trim(),
        discount_percentage: 0,
        labor_cost: 0,
        products: selectedProductData,
        notes: `${selectedProductData.length} ürün ile oluşturulan teklif`
      };

      const response = await fetch(`${API}/quotes`, {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json',
        },
        body: JSON.stringify(quoteData)
      });

      if (!response.ok) {
        throw new Error('Teklif oluşturulamadı');
      }

      const savedQuote = await response.json();

      // Teklifleri yeniden yükle
      await fetchQuotes();

      // Dialog'u kapat ve formu temizle
      setShowQuickQuoteDialog(false);
      setQuickQuoteCustomerName('');
      
      // Seçimi temizle
      clearSelection();

      // Teklifler sekmesine geç
      setActiveTab('quotes');

      toast.success(`"${savedQuote.name}" teklifi başarıyla oluşturuldu!`);

    } catch (error) {
      console.error('Hızlı teklif oluşturma hatası:', error);
      toast.error('Teklif oluşturulamadı: ' + error.message);
    }
  };

  // Upload History fonksiyonları
  const fetchUploadHistory = async (companyId) => {
    try {
      setLoadingHistory(true);
      const response = await axios.get(`${API}/companies/${companyId}/upload-history`);
      setUploadHistory(response.data);
    } catch (error) {
      console.error('Upload geçmişi yüklenirken hata:', error);
      toast.error('Upload geçmişi yüklenemedi');
      setUploadHistory([]);
    } finally {
      setLoadingHistory(false);
    }
  };

  const openUploadHistoryDialog = async (company) => {
    setSelectedCompanyForHistory(company);
    setShowUploadHistoryDialog(true);
    await fetchUploadHistory(company.id);
  };

  const closeUploadHistoryDialog = () => {
    setShowUploadHistoryDialog(false);
    setSelectedCompanyForHistory(null);
    setUploadHistory([]);
  };

  // Para birimi değiştirme fonksiyonları
  const openCurrencyChangeDialog = (upload) => {
    setSelectedUploadForCurrency(upload);
    setNewCurrency('USD'); // Default selection
    setShowCurrencyChangeDialog(true);
  };

  const closeCurrencyChangeDialog = () => {
    setShowCurrencyChangeDialog(false);
    setSelectedUploadForCurrency(null);
    setNewCurrency('USD');
  };

  const changeCurrency = async () => {
    if (!selectedUploadForCurrency || !newCurrency) {
      toast.error('Lütfen geçerli bir para birimi seçin');
      return;
    }

    try {
      setChangingCurrency(true);
      
      const response = await axios.post(
        `${API}/upload-history/${selectedUploadForCurrency.id}/change-currency?new_currency=${newCurrency}`
      );

      if (response.data.success) {
        toast.success(response.data.message);
        
        // Upload geçmişini yenile
        await fetchUploadHistory(selectedCompanyForHistory.id);
        
        // Ürünleri yenile (para birimi değişikliği nedeniyle)
        await loadProducts();
        
        // Dialog'u kapat
        closeCurrencyChangeDialog();
      } else {
        toast.error('Para birimi güncellenemedi');
      }

    } catch (error) {
      console.error('Para birimi değiştirme hatası:', error);
      toast.error(error.response?.data?.detail || 'Para birimi güncellenemedi');
    } finally {
      setChangingCurrency(false);
    }
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
    
    // Hangi fiyatı kullanacağımızı belirle (indirimli fiyat gösterim durumuna göre)
    const totalListPrice = selectedProductsData.reduce((sum, p) => {
      let price = 0;
      if (showQuoteDiscountedPrices && p.discounted_price_try) {
        // İndirimli fiyat gösteriliyorsa ve indirimli fiyat varsa onu kullan
        price = parseFloat(p.discounted_price_try) || 0;
      } else {
        // Yoksa liste fiyatını kullan
        price = parseFloat(p.list_price_try) || 0;
      }
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
      totalWithLaborAndDiscount: isNaN(totalNetPrice) ? 0 : totalNetPrice,
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
      return '0';
    }
    return new Intl.NumberFormat('tr-TR', { 
      style: 'decimal', 
      minimumFractionDigits: 0,  // Ondalık kısım gösterme
      maximumFractionDigits: 0   // Maksimum ondalık da 0
    }).format(Math.round(price));  // Yuvarlayarak tam sayı yap
  };

  const formatExchangeRate = (rate) => {
    // Handle NaN, null, undefined cases
    if (isNaN(rate) || rate === null || rate === undefined) {
      return '0.00';
    }
    return new Intl.NumberFormat('tr-TR', { 
      style: 'decimal', 
      minimumFractionDigits: 2,  // En az 2 ondalık göster
      maximumFractionDigits: 2   // En fazla 2 ondalık göster
    }).format(Number(rate));
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
          <div className="flex items-center gap-4 mb-2">
            <img 
              src="/logo.png" 
              alt="Çorlu Karavan Logo" 
              className="w-16 h-16 object-contain"
            />
            <div className="flex-1">
              <h1 className="text-4xl font-bold text-slate-800">
                Çorlu Karavan
              </h1>
              <div className="flex items-center gap-3">
                <p className="text-lg text-slate-600">Fiyat Takip Sistemi</p>
                <span className="text-xs text-slate-400 font-light">made by Mehmet Necdet</span>
              </div>
            </div>
          </div>
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
                    {exchangeRates.USD ? formatExchangeRate(exchangeRates.USD) : '---'}
                  </span>
                </div>
                <div className="flex justify-between items-center">
                  <span className="text-sm text-emerald-700">EUR/TRY:</span>
                  <span className="text-lg font-bold text-emerald-900">
                    {exchangeRates.EUR ? formatExchangeRate(exchangeRates.EUR) : '---'}
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

        <Tabs value={activeTab} onValueChange={setActiveTab} className="space-y-6">
          <TabsList className="grid w-full grid-cols-5 h-16 p-1 bg-slate-100 rounded-xl">
            <TabsTrigger 
              value="products" 
              className="h-14 text-base font-medium transition-all duration-200 data-[state=active]:bg-blue-500 data-[state=active]:text-white data-[state=active]:shadow-lg hover:bg-blue-100 text-blue-700 rounded-lg"
            >
              <div className="flex items-center gap-2">
                <Package className="w-5 h-5" />
                Ürünler
              </div>
            </TabsTrigger>
            <TabsTrigger 
              value="quotes"
              className="h-14 text-base font-medium transition-all duration-200 data-[state=active]:bg-purple-500 data-[state=active]:text-white data-[state=active]:shadow-lg hover:bg-purple-100 text-purple-700 rounded-lg"
            >
              <div className="flex items-center gap-2">
                <FileText className="w-5 h-5" />
                Teklifler
                {selectedProducts.size > 0 && (
                  <Badge variant="secondary" className="ml-1 bg-white text-purple-700">
                    {selectedProducts.size}
                  </Badge>
                )}
              </div>
            </TabsTrigger>
            <TabsTrigger 
              value="companies"
              className="h-14 text-base font-medium transition-all duration-200 data-[state=active]:bg-orange-500 data-[state=active]:text-white data-[state=active]:shadow-lg hover:bg-orange-100 text-orange-700 rounded-lg"
            >
              <div className="flex items-center gap-2">
                <Building2 className="w-5 h-5" />
                Firmalar
              </div>
            </TabsTrigger>
            <TabsTrigger 
              value="categories"
              className="h-14 text-base font-medium transition-all duration-200 data-[state=active]:bg-teal-500 data-[state=active]:text-white data-[state=active]:shadow-lg hover:bg-teal-100 text-teal-700 rounded-lg"
            >
              <div className="flex items-center gap-2">
                <Tags className="w-5 h-5" />
                Kategoriler
              </div>
            </TabsTrigger>
            <TabsTrigger 
              value="upload"
              className="h-14 text-base font-medium transition-all duration-200 data-[state=active]:bg-emerald-500 data-[state=active]:text-white data-[state=active]:shadow-lg hover:bg-emerald-100 text-emerald-700 rounded-lg"
            >
              <div className="flex items-center gap-2">
                <Upload className="w-5 h-5" />
                Excel Yükle
              </div>
            </TabsTrigger>
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
                        <div className="flex gap-2 flex-wrap">
                          <Button
                            variant="outline"
                            size="sm"
                            onClick={() => openUploadHistoryDialog(company)}
                            className="bg-blue-50 hover:bg-blue-100 text-blue-700"
                          >
                            <Archive className="w-4 h-4 mr-2" />
                            Geçmiş
                          </Button>
                          <Button
                            variant="destructive"
                            size="sm"
                            onClick={() => deleteCompany(company.id)}
                          >
                            <Trash2 className="w-4 h-4 mr-2" />
                            Sil
                          </Button>
                        </div>
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
                            <Package className="w-4 h-4 mr-1" />
                            Ürünleri Göster
                          </Button>
                          <Button
                            variant="outline"
                            size="sm"
                            onClick={() => openCategoryProductDialog(category)}
                            className="bg-blue-50 hover:bg-blue-100 text-blue-700"
                          >
                            <Plus className="w-4 h-4 mr-1" />
                            Ürün Ekle
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
                  {/* Firma Seçim Modu */}
                  <div>
                    <Label>Firma Seçimi</Label>
                    <div className="flex gap-4 mt-2">
                      <label className="flex items-center space-x-2">
                        <input
                          type="radio"
                          name="companyMode"
                          checked={useExistingCompany}
                          onChange={() => setUseExistingCompany(true)}
                          className="text-emerald-600"
                        />
                        <span>Mevcut Firma</span>
                      </label>
                      <label className="flex items-center space-x-2">
                        <input
                          type="radio"
                          name="companyMode"
                          checked={!useExistingCompany}
                          onChange={() => setUseExistingCompany(false)}
                          className="text-emerald-600"
                        />
                        <span>Yeni Firma</span>
                      </label>
                    </div>
                  </div>

                  {/* Mevcut Firma Seçimi */}
                  {useExistingCompany && (
                    <div>
                      <Label htmlFor="company-select">Mevcut Firmalardan Seçin</Label>
                      <Select value={selectedCompany} onValueChange={setSelectedCompany}>
                        <SelectTrigger>
                          <SelectValue placeholder="Firma seçin..." />
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
                  )}

                  {/* Yeni Firma Adı Girişi */}
                  {!useExistingCompany && (
                    <div>
                      <Label htmlFor="new-company-name">Yeni Firma Adı</Label>
                      <Input
                        id="new-company-name"
                        placeholder="Firma adını girin..."
                        value={uploadCompanyName}
                        onChange={(e) => setUploadCompanyName(e.target.value)}
                        className="w-full"
                      />
                      <p className="text-sm text-slate-500 mt-1">
                        Bu firma otomatik olarak oluşturulacak ve ürünler bu firmaya atanacak
                      </p>
                    </div>
                  )}

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
                    disabled={loading || (!selectedCompany && useExistingCompany) || (!uploadCompanyName.trim() && !useExistingCompany) || !uploadFile}
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
                          onClick={() => setShowQuickQuoteDialog(true)}
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
                              <SelectItem value="none">Kategorisiz</SelectItem>
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

                    return sortedGroups.map(([categoryId, categoryProducts], index) => {
                      const category = categories.find(c => c.id === categoryId);
                      const categoryName = category ? category.name : 'Kategorisiz Ürünler';
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
                            {/* İndirimli Fiyat Toggle Butonu - Sadece ilk kategoride göster */}
                            {index === 0 && (
                              <Button
                                variant="outline"
                                size="sm"
                                onClick={() => setShowDiscountedPrices(!showDiscountedPrices)}
                                className="ml-2 p-2"
                                title={showDiscountedPrices ? "İndirimli fiyatları gizle" : "İndirimli fiyatları göster"}
                              >
                                {showDiscountedPrices ? (
                                  <EyeOff className="w-4 h-4" />
                                ) : (
                                  <Eye className="w-4 h-4" />
                                )}
                              </Button>
                            )}
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
                                  {showDiscountedPrices && <TableHead>İndirimli Fiyat</TableHead>}
                                  <TableHead>Para Birimi</TableHead>
                                  <TableHead>TL Fiyat</TableHead>
                                  {showDiscountedPrices && <TableHead>TL İndirimli</TableHead>}
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
                                                <SelectItem value="none">Kategorisiz</SelectItem>
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
                                      {showDiscountedPrices && (
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
                                      )}
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
                                      {showDiscountedPrices && (
                                        <TableCell>
                                          {product.discounted_price_try ? (
                                            `₺ ${formatPrice(product.discounted_price_try)}`
                                          ) : '-'}
                                        </TableCell>
                                      )}
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
                      <div className="flex items-center justify-between mb-2">
                        <h4 className="font-semibold text-blue-900">
                          Seçili Ürünler ({selectedProducts.size} çeşit, {calculateQuoteTotals().totalQuantity} adet)
                        </h4>
                        {/* Teklif İndirimli Fiyat Toggle Butonu */}
                        <Button
                          variant="outline"
                          size="sm"
                          onClick={() => setShowQuoteDiscountedPrices(!showQuoteDiscountedPrices)}
                          className="p-1 ml-2"
                          title={showQuoteDiscountedPrices ? "İndirimli fiyatları gizle" : "İndirimli fiyatları göster"}
                        >
                          {showQuoteDiscountedPrices ? (
                            <EyeOff className="w-3 h-3" />
                          ) : (
                            <Eye className="w-3 h-3" />
                          )}
                        </Button>
                      </div>
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
                                  {showQuoteDiscountedPrices && product.discounted_price_try ? (
                                    // İndirimli fiyat varsa ve gösterilmesi isteniyorsa
                                    <>
                                      <div className="font-medium text-green-600">₺ {formatPrice((product.discounted_price_try || 0) * (product.quantity || 1))}</div>
                                      <div className="text-xs text-slate-500 line-through">
                                        ₺ {formatPrice((product.list_price_try || 0) * (product.quantity || 1))} (Liste)
                                      </div>
                                      <div className="text-xs text-green-600">
                                        ₺ {formatPrice(product.discounted_price_try || 0)} × {product.quantity || 1}
                                      </div>
                                    </>
                                  ) : (
                                    // Liste fiyatı veya indirimli fiyat gizliyse
                                    <>
                                      <div className="font-medium">₺ {formatPrice((product.list_price_try || 0) * (product.quantity || 1))}</div>
                                      <div className="text-xs text-slate-500">
                                        ₺ {formatPrice(product.list_price_try || 0)} × {product.quantity || 1}
                                      </div>
                                    </>
                                  )}
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

                    {/* İndirim Bölümü - Küçültülmüş */}
                    <div className="bg-amber-50 border border-amber-200 rounded-lg p-3">
                      <div className="flex items-center justify-between">
                        <div className="flex items-center gap-2">
                          <TrendingUp className="w-4 h-4 text-amber-600" />
                          <span className="font-medium text-amber-900 text-sm">İndirim</span>
                        </div>
                        <div className="flex items-center gap-2">
                          <Input
                            type="number"
                            min="0"
                            max="100"
                            step="1"
                            placeholder="0"
                            value={quoteDiscount}
                            onChange={(e) => setQuoteDiscount(parseFloat(e.target.value) || 0)}
                            className="w-16 text-sm"
                          />
                          <span className="text-amber-700 text-sm">%</span>
                        </div>
                        <div className="flex gap-1">
                          <Button
                            variant="outline"
                            size="sm"
                            onClick={() => setQuoteDiscount(10)}
                            className="text-xs px-2"
                          >
                            10%
                          </Button>
                          <Button
                            variant="outline"
                            size="sm"
                            onClick={() => setQuoteDiscount(15)}
                            className="text-xs px-2"
                          >
                            15%
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
                            onKeyDown={(e) => {
                              if (e.key === 'Enter' && quoteLaborCost > 0) {
                                // Enter'a basınca işçilik maliyeti entegre edilir
                                toast.success(`₺${formatPrice(quoteLaborCost)} işçilik maliyeti eklendi!`);
                              }
                            }}
                            className="w-32"
                          />
                          {/* Yeşil Tik Butonu */}
                          {quoteLaborCost > 0 && (
                            <Button
                              size="sm"
                              onClick={() => {
                                toast.success(`₺${formatPrice(quoteLaborCost)} işçilik maliyeti eklendi!`);
                              }}
                              className="bg-green-600 hover:bg-green-700 px-2"
                            >
                              <Check className="w-4 h-4" />
                            </Button>
                          )}
                        </div>
                        <div className="flex gap-2 ml-auto">
                          <Button
                            variant="outline"
                            size="sm"
                            onClick={() => setQuoteLaborCost(2000)}
                          >
                            ₺2000
                          </Button>
                          <Button
                            variant="outline"
                            size="sm"
                            onClick={() => setQuoteLaborCost(5000)}
                          >
                            ₺5000
                          </Button>
                          <Button
                            variant="outline"
                            size="sm"
                            onClick={() => setQuoteLaborCost(10000)}
                          >
                            ₺10000
                          </Button>
                          <Button
                            variant="outline"
                            size="sm"
                            onClick={() => setQuoteLaborCost(20000)}
                          >
                            ₺20000
                          </Button>
                        </div>
                      </div>
                    </div>

                    {/* Quote Summary */}
                    <div className="bg-emerald-50 border border-emerald-200 rounded-lg p-4">
                      <h4 className="font-semibold text-emerald-900 mb-3">Teklif Özeti</h4>
                      <div className="grid grid-cols-2 md:grid-cols-5 gap-4">
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
                        {quoteLaborCost > 0 && (
                          <div className="text-center">
                            <div className="text-2xl font-bold text-green-600">
                              + ₺ {formatPrice(calculateQuoteTotals().laborCost)}
                            </div>
                            <div className="text-sm text-green-500">İşçilik</div>
                          </div>
                        )}
                        <div className="text-center">
                          <div className="text-2xl font-bold text-emerald-800">
                            ₺ {formatPrice(calculateQuoteTotals().totalNetPrice)}
                          </div>
                          <div className="text-sm text-emerald-600">Net Toplam</div>
                        </div>
                      </div>
                      
                      {(quoteDiscount > 0 || quoteLaborCost > 0) && (
                        <div className="mt-4 p-3 bg-white rounded border border-emerald-300">
                          <div className="text-sm text-emerald-700">
                            {quoteDiscount > 0 && (
                              <div><strong>İndirim:</strong> Liste fiyatı üzerinden %{quoteDiscount} indirim uygulandı. Tasarruf: <strong>₺ {formatPrice(calculateQuoteTotals().discountAmount)}</strong></div>
                            )}
                            {quoteLaborCost > 0 && (
                              <div><strong>İşçilik:</strong> Ek işçilik maliyeti eklendi. Tutar: <strong>₺ {formatPrice(calculateQuoteTotals().laborCost)}</strong></div>
                            )}
                          </div>
                        </div>
                      )}
                    </div>

                    {/* Action Buttons - Yeni Tasarım */}
                    <div className="flex gap-3">
                      {/* Ana PDF İndirme Butonu */}
                      <Button 
                        onClick={async () => {
                          try {
                            let quoteId = null;
                            
                            // Eğer mevcut bir teklif yüklenmişse onu güncelle
                            if (loadedQuote && loadedQuote.id && (quoteLaborCost > 0 || quoteDiscount > 0)) {
                              const updateResponse = await fetch(`${API}/quotes/${loadedQuote.id}`, {
                                method: 'PUT',
                                headers: {
                                  'Content-Type': 'application/json',
                                },
                                body: JSON.stringify({
                                  labor_cost: parseFloat(quoteLaborCost) || 0,
                                  discount_percentage: parseFloat(quoteDiscount) || 0
                                })
                              });
                              
                              if (!updateResponse.ok) {
                                throw new Error('Teklif güncellenemedi');
                              }
                              
                              const updatedQuote = await updateResponse.json();
                              quoteId = updatedQuote.id;
                              
                              toast.success(`"${loadedQuote.name}" teklifi güncellendi!`);
                            } else {
                              // Yeni teklif oluştur
                              const selectedProductData = getSelectedProductsData().map(p => ({
                                id: p.id,
                                quantity: p.quantity || 1
                              }));
                              
                              const newQuoteData = {
                                name: loadedQuote?.name || quoteName || `Teklif - ${new Date().toLocaleDateString('tr-TR')}`,
                                discount_percentage: parseFloat(quoteDiscount) || 0,
                                labor_cost: parseFloat(quoteLaborCost) || 0,
                                products: selectedProductData,
                                notes: quoteLaborCost > 0 ? `İşçilik maliyeti: ₺${formatPrice(quoteLaborCost)}` : null
                              };
                              
                              const createResponse = await fetch(`${API}/quotes`, {
                                method: 'POST',
                                headers: {
                                  'Content-Type': 'application/json',
                                },
                                body: JSON.stringify(newQuoteData)
                              });
                              
                              if (!createResponse.ok) {
                                throw new Error('Teklif oluşturulamadı');
                              }
                              
                              const savedQuote = await createResponse.json();
                              quoteId = savedQuote.id;
                              
                              toast.success('Teklif başarıyla oluşturuldu!');
                            }
                            
                            // PDF'i hemen indir
                            const pdfUrl = `${API}/quotes/${quoteId}/pdf`;
                            const link = document.createElement('a');
                            link.href = pdfUrl;
                            link.download = `${loadedQuote?.name || quoteName || 'Teklif'}.pdf`;
                            document.body.appendChild(link);
                            link.click();
                            document.body.removeChild(link);
                            
                            // Teklifleri yenile
                            await fetchQuotes();
                            
                          } catch (error) {
                            console.error('PDF oluşturma hatası:', error);
                            toast.error('PDF oluşturulamadı: ' + error.message);
                          }
                        }}
                        className="bg-green-600 hover:bg-green-700 flex-1"
                      >
                        <Download className="w-4 h-4 mr-2" />
                        {quoteLaborCost > 0 ? 'İşçilikli PDF İndir' : 'PDF İndir'}
                      </Button>
                      
                      {/* Değişiklik Varsa Teklifi Kaydet Butonu */}
                      {(quoteDiscount > 0 || quoteLaborCost > 0) && (
                        <Button 
                          onClick={async () => {
                            try {
                              const selectedProductData = getSelectedProductsData().map(p => ({
                                id: p.id,
                                quantity: p.quantity || 1
                              }));
                              
                              const newQuoteData = {
                                name: loadedQuote?.name || quoteName || `Teklif - ${new Date().toLocaleDateString('tr-TR')}`,
                                discount_percentage: parseFloat(quoteDiscount) || 0,
                                labor_cost: parseFloat(quoteLaborCost) || 0,
                                products: selectedProductData,
                                notes: `${quoteDiscount > 0 ? `%${quoteDiscount} indirim` : ''}${quoteLaborCost > 0 ? ` | ₺${formatPrice(quoteLaborCost)} işçilik` : ''}`
                              };
                              
                              const response = await fetch(`${API}/quotes`, {
                                method: 'POST',
                                headers: {
                                  'Content-Type': 'application/json',
                                },
                                body: JSON.stringify(newQuoteData)
                              });
                              
                              if (!response.ok) {
                                throw new Error('Teklif kaydedilemedi');
                              }
                              
                              const savedQuote = await response.json();
                              
                              toast.success('Teklif başarıyla kaydedildi!');
                              
                              // Teklifleri yenile
                              await fetchQuotes();
                              
                            } catch (error) {
                              console.error('Teklif kaydetme hatası:', error);
                              toast.error('Teklif kaydedilemedi: ' + error.message);
                            }
                          }}
                          className="bg-blue-600 hover:bg-blue-700"
                        >
                          <Archive className="w-4 h-4 mr-2" />
                          Teklifi Kaydet
                        </Button>
                      )}
                      
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
                                  {quote.labor_cost > 0 && (
                                    <span className="text-green-600"> • ₺{formatPrice(quote.labor_cost)} işçilik</span>
                                  )}
                                </p>
                                <div className="flex items-center gap-4 mt-2 text-sm text-slate-600">
                                  <span>Ara Toplam: ₺{formatPrice(quote.total_discounted_price)}</span>
                                  {quote.labor_cost > 0 && (
                                    <span className="text-green-600">İşçilik: ₺{formatPrice(quote.labor_cost)}</span>
                                  )}
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
                                    setQuoteLaborCost(quote.labor_cost || 0); // İşçilik maliyetini de yükle
                                    setLoadedQuote(quote); // Yüklenen teklifi kaydet
                                    setQuoteName(quote.name); // Teklif adını da yükle
                                    toast.success(`"${quote.name}" teklifi yüklendi ${quote.labor_cost > 0 ? `(₺${formatPrice(quote.labor_cost)} işçilik dahil)` : ''}`);
                                  }}
                                >
                                  Yükle
                                </Button>
                                <Button
                                  variant="secondary"
                                  size="sm"
                                  onClick={() => {
                                    try {
                                      // Teklifi önce yükle
                                      const productIds = new Map();
                                      quote.products.forEach(p => productIds.set(p.id, 1));
                                      setSelectedProducts(productIds);
                                      setQuoteDiscount(quote.discount_percentage);
                                      setQuoteLaborCost(quote.labor_cost || 0);
                                      setLoadedQuote(quote);
                                      setQuoteName(quote.name);
                                      
                                      toast.success(`"${quote.name}" teklifi yüklendi`);
                                      
                                    } catch (error) {
                                      console.error('Teklif yükleme hatası:', error);
                                      toast.error('Teklif yükleme işlemi başarısız oldu');
                                    }
                                  }}
                                  className="bg-green-100 text-green-800 hover:bg-green-200"
                                  title={`"${quote.name}" teklifini düzenleme için yükle`}
                                >
                                  📝 Yükle
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

            {/* Para Birimi Değiştirme Dialog */}
            <Dialog open={showCurrencyChangeDialog} onOpenChange={closeCurrencyChangeDialog}>
              <DialogContent className="max-w-md">
                <DialogHeader>
                  <DialogTitle>Para Birimini Değiştir</DialogTitle>
                  <DialogDescription>
                    {selectedUploadForCurrency?.filename} dosyasındaki tüm ürünlerin para birimini değiştirin
                  </DialogDescription>
                </DialogHeader>
                
                <div className="py-4 space-y-4">
                  {selectedUploadForCurrency && (
                    <div className="p-4 bg-slate-50 rounded-lg">
                      <div className="text-sm font-medium mb-2">Mevcut Para Birimi Dağılımı:</div>
                      <div className="flex gap-2 flex-wrap">
                        {Object.entries(selectedUploadForCurrency.currency_distribution || {}).map(([currency, count]) => (
                          <Badge key={currency} variant="outline">
                            {currency}: {count} ürün
                          </Badge>
                        ))}
                      </div>
                    </div>
                  )}
                  
                  <div>
                    <Label htmlFor="new-currency">Yeni Para Birimi</Label>
                    <Select value={newCurrency} onValueChange={setNewCurrency}>
                      <SelectTrigger>
                        <SelectValue placeholder="Para birimi seçin" />
                      </SelectTrigger>
                      <SelectContent>
                        <SelectItem value="USD">USD - Amerikan Doları</SelectItem>
                        <SelectItem value="EUR">EUR - Euro</SelectItem>
                        <SelectItem value="TRY">TRY - Türk Lirası</SelectItem>
                        <SelectItem value="GBP">GBP - İngiliz Sterlini</SelectItem>
                      </SelectContent>
                    </Select>
                  </div>
                  
                  <div className="p-3 bg-amber-50 border border-amber-200 rounded-lg">
                    <div className="flex items-start gap-2">
                      <AlertTriangle className="w-4 h-4 text-amber-600 mt-0.5" />
                      <div className="text-sm text-amber-700">
                        <strong>Uyarı:</strong> Bu işlem geri alınamaz! Tüm ürünlerin fiyatları güncel döviz kurlarına göre dönüştürülecek.
                      </div>
                    </div>
                  </div>
                </div>
                
                <div className="flex gap-2 justify-end">
                  <Button variant="outline" onClick={closeCurrencyChangeDialog}>
                    İptal
                  </Button>
                  <Button 
                    onClick={changeCurrency} 
                    disabled={changingCurrency || !newCurrency}
                    className="bg-yellow-600 hover:bg-yellow-700"
                  >
                    {changingCurrency ? (
                      <>
                        <RefreshCw className="w-4 h-4 mr-2 animate-spin" />
                        Değiştiriliyor...
                      </>
                    ) : (
                      <>
                        <RefreshCw className="w-4 h-4 mr-2" />
                        Para Birimini Değiştir
                      </>
                    )}
                  </Button>
                </div>
              </DialogContent>
            </Dialog>

            {/* Upload History Dialog */}
            <Dialog open={showUploadHistoryDialog} onOpenChange={closeUploadHistoryDialog}>
              <DialogContent className="max-w-4xl max-h-[80vh] overflow-y-auto">
                <DialogHeader>
                  <DialogTitle>
                    {selectedCompanyForHistory?.name} - Upload Geçmişi
                  </DialogTitle>
                  <DialogDescription>
                    Bu firmaya ait tüm Excel yükleme işlemleri ve detayları
                  </DialogDescription>
                </DialogHeader>
                
                {loadingHistory ? (
                  <div className="flex items-center justify-center py-8">
                    <RefreshCw className="w-6 h-6 animate-spin mr-2" />
                    Yükleniyor...
                  </div>
                ) : uploadHistory.length === 0 ? (
                  <div className="text-center py-8 text-slate-500">
                    Bu firma için henüz upload geçmişi bulunmuyor
                  </div>
                ) : (
                  <div className="space-y-4">
                    {uploadHistory.map((upload) => (
                      <Card key={upload.id} className="border-slate-200">
                        <CardHeader className="pb-3">
                          <div className="flex justify-between items-start">
                            <div>
                              <CardTitle className="text-base">{upload.filename}</CardTitle>
                              <CardDescription>
                                {new Date(upload.upload_date).toLocaleDateString('tr-TR', {
                                  year: 'numeric',
                                  month: 'long',
                                  day: 'numeric',
                                  hour: '2-digit',
                                  minute: '2-digit'
                                })}
                              </CardDescription>
                            </div>
                            <Badge variant={upload.status === 'completed' ? 'default' : 'destructive'}>
                              {upload.status === 'completed' ? 'Tamamlandı' : 'Hata'}
                            </Badge>
                          </div>
                        </CardHeader>
                        <CardContent>
                          <div className="grid grid-cols-2 md:grid-cols-4 gap-4 mb-4">
                            <div className="text-center">
                              <div className="text-2xl font-bold text-emerald-600">
                                {upload.total_products}
                              </div>
                              <div className="text-sm text-slate-500">Toplam Ürün</div>
                            </div>
                            <div className="text-center">
                              <div className="text-2xl font-bold text-blue-600">
                                {upload.new_products}
                              </div>
                              <div className="text-sm text-slate-500">Yeni Ürün</div>
                            </div>
                            <div className="text-center">
                              <div className="text-2xl font-bold text-orange-600">
                                {upload.updated_products}
                              </div>
                              <div className="text-sm text-slate-500">Güncellenmiş</div>
                            </div>
                            <div className="text-center">
                              <div className="text-2xl font-bold text-purple-600">
                                {upload.price_changes?.length || 0}
                              </div>
                              <div className="text-sm text-slate-500">Fiyat Değişikliği</div>
                            </div>
                          </div>

                          {/* Para Birimi Dağılımı */}
                          {upload.currency_distribution && Object.keys(upload.currency_distribution).length > 0 && (
                            <div className="mb-4">
                              <h4 className="text-sm font-medium mb-2">Para Birimi Dağılımı:</h4>
                              <div className="flex gap-2 flex-wrap">
                                {Object.entries(upload.currency_distribution).map(([currency, count]) => (
                                  <Badge key={currency} variant="outline">
                                    {currency}: {count} ürün
                                  </Badge>
                                ))}
                              </div>
                            </div>
                          )}

                          {/* Fiyat Değişiklikleri */}
                          {upload.price_changes && upload.price_changes.length > 0 && (
                            <div>
                              <h4 className="text-sm font-medium mb-2">Fiyat Değişiklikleri:</h4>
                              <div className="max-h-32 overflow-y-auto space-y-1">
                                {upload.price_changes.slice(0, 5).map((change, index) => (
                                  <div key={index} className="text-sm p-2 bg-slate-50 rounded">
                                    <span className="font-medium">{change.product_name}</span>
                                    <span className={`ml-2 ${change.change_type === 'increase' ? 'text-red-600' : 'text-green-600'}`}>
                                      {change.old_price} → {change.new_price} {change.currency}
                                      ({change.change_type === 'increase' ? '+' : ''}{change.change_percent}%)
                                    </span>
                                  </div>
                                ))}
                                {upload.price_changes.length > 5 && (
                                  <div className="text-xs text-slate-500 text-center">
                                    ve {upload.price_changes.length - 5} değişiklik daha...
                                  </div>
                                )}
                              </div>
                            </div>
                          )}

                          {/* Para Birimi Değiştirme Butonu */}
                          <div className="mt-4 pt-4 border-t border-slate-200">
                            <div className="flex justify-between items-center">
                              <div className="text-sm text-slate-600">
                                Bu listedeki tüm ürünlerin para birimini değiştir
                              </div>
                              <Button
                                variant="outline"
                                size="sm"
                                onClick={() => openCurrencyChangeDialog(upload)}
                                className="bg-yellow-50 hover:bg-yellow-100 text-yellow-800 border-yellow-200"
                              >
                                <RefreshCw className="w-4 h-4 mr-2" />
                                Para Birimini Değiştir
                              </Button>
                            </div>
                          </div>
                        </CardContent>
                      </Card>
                    ))}
                  </div>
                )}
              </DialogContent>
            </Dialog>

        </Tabs>
      </div>

      {/* Kategori Ürün Atama Dialog'u */}
      <Dialog open={showCategoryProductDialog} onOpenChange={setShowCategoryProductDialog}>
        <DialogContent className="max-w-4xl max-h-[80vh] overflow-y-auto">
          <DialogHeader>
            <DialogTitle className="flex items-center gap-2">
              <div 
                className="w-4 h-4 rounded-full" 
                style={{backgroundColor: selectedCategoryForProducts?.color}}
              ></div>
              "{selectedCategoryForProducts?.name}" Kategorisine Ürün Ekle
            </DialogTitle>
            <DialogDescription>
              Kategorisi olmayan {uncategorizedProducts.length} ürün arasından seçim yapabilirsiniz
            </DialogDescription>
          </DialogHeader>
          
          <div className="py-4">
            {uncategorizedProducts.length === 0 ? (
              <div className="text-center py-8 text-slate-500">
                <Package className="w-12 h-12 mx-auto mb-4 text-slate-400" />
                <p>Kategorisi olmayan ürün bulunmuyor.</p>
                <p className="text-sm">Tüm ürünler zaten kategorilere atanmış.</p>
              </div>
            ) : (
              <>
                {/* Tümünü Seç/Bırak Butonu */}
                <div className="flex items-center justify-between mb-4 pb-4 border-b">
                  <p className="text-sm text-slate-600">
                    {selectedProductsForCategory.size} / {uncategorizedProducts.length} ürün seçildi
                  </p>
                  <div className="space-x-2">
                    <Button
                      variant="outline"
                      size="sm"
                      onClick={() => {
                        const allIds = new Set(uncategorizedProducts.map(p => p.id));
                        setSelectedProductsForCategory(allIds);
                      }}
                    >
                      Tümünü Seç
                    </Button>
                    <Button
                      variant="outline"
                      size="sm"
                      onClick={() => setSelectedProductsForCategory(new Set())}
                    >
                      Seçimi Temizle
                    </Button>
                  </div>
                </div>

                {/* Ürün Listesi */}
                <div className="space-y-2 max-h-96 overflow-y-auto">
                  {uncategorizedProducts.map((product) => {
                    const company = companies.find(c => c.id === product.company_id);
                    const isSelected = selectedProductsForCategory.has(product.id);
                    
                    return (
                      <div
                        key={product.id}
                        className={`flex items-center p-3 rounded-lg border transition-colors cursor-pointer ${
                          isSelected 
                            ? 'bg-blue-50 border-blue-200' 
                            : 'bg-white border-slate-200 hover:bg-slate-50'
                        }`}
                        onClick={() => {
                          const newSelected = new Set(selectedProductsForCategory);
                          if (isSelected) {
                            newSelected.delete(product.id);
                          } else {
                            newSelected.add(product.id);
                          }
                          setSelectedProductsForCategory(newSelected);
                        }}
                      >
                        <input
                          type="checkbox"
                          checked={isSelected}
                          onChange={() => {}} // Handled by div onClick
                          className="mr-3"
                        />
                        <div className="flex-1">
                          <div className="font-medium text-slate-900">{product.name}</div>
                          <div className="text-sm text-slate-500">
                            {company?.name || 'Bilinmeyen Firma'} • ₺ {formatPrice(product.list_price_try || 0)}
                          </div>
                        </div>
                        {isSelected && (
                          <Check className="w-5 h-5 text-blue-600" />
                        )}
                      </div>
                    );
                  })}
                </div>
              </>
            )}
          </div>
          
          <DialogFooter>
            <Button 
              variant="outline" 
              onClick={() => {
                setShowCategoryProductDialog(false);
                setSelectedProductsForCategory(new Set());
              }}
            >
              İptal
            </Button>
            {selectedProductsForCategory.size > 0 && (
              <Button 
                onClick={assignProductsToCategory}
                className="bg-blue-600 hover:bg-blue-700"
              >
                <Plus className="w-4 h-4 mr-2" />
                {selectedProductsForCategory.size} Ürünü Kategoriye Ekle
              </Button>
            )}
          </DialogFooter>
        </DialogContent>
      </Dialog>

      {/* Hızlı Teklif Oluşturma Dialog'u */}
      <Dialog open={showQuickQuoteDialog} onOpenChange={setShowQuickQuoteDialog}>
        <DialogContent className="max-w-md">
          <DialogHeader>
            <DialogTitle className="flex items-center gap-2">
              <FileText className="w-5 h-5 text-blue-600" />
              Hızlı Teklif Oluştur
            </DialogTitle>
            <DialogDescription>
              {selectedProducts.size} seçili ürün için teklif oluşturuluyor
            </DialogDescription>
          </DialogHeader>
          
          <div className="py-4">
            <div className="space-y-4">
              {/* Müşteri Adı */}
              <div>
                <Label htmlFor="customer-name">Müşteri Adı *</Label>
                <Input
                  id="customer-name"
                  placeholder="Örn: Mehmet Yılmaz"
                  value={quickQuoteCustomerName}
                  onChange={(e) => setQuickQuoteCustomerName(e.target.value)}
                  onKeyDown={(e) => {
                    if (e.key === 'Enter' && quickQuoteCustomerName.trim()) {
                      createQuickQuote();
                    }
                  }}
                  className="mt-1"
                  autoFocus
                />
              </div>

              {/* Seçili Ürün Özeti */}
              <div className="bg-slate-50 rounded-lg p-3">
                <div className="text-sm font-medium text-slate-700 mb-2">Seçili Ürün Özeti:</div>
                <div className="space-y-1 max-h-32 overflow-y-auto">
                  {getSelectedProductsData().slice(0, 3).map((product, index) => (
                    <div key={product.id} className="text-xs text-slate-600 flex justify-between">
                      <span className="truncate">{product.name}</span>
                      <span>₺{formatPrice(product.list_price_try || 0)}</span>
                    </div>
                  ))}
                  {selectedProducts.size > 3 && (
                    <div className="text-xs text-slate-500 italic">
                      ... ve {selectedProducts.size - 3} ürün daha
                    </div>
                  )}
                </div>
                <div className="mt-2 pt-2 border-t text-sm font-medium">
                  Toplam: ₺{formatPrice(calculateQuoteTotals().totalListPrice)}
                </div>
              </div>
            </div>
          </div>
          
          <DialogFooter>
            <Button 
              variant="outline" 
              onClick={() => {
                setShowQuickQuoteDialog(false);
                setQuickQuoteCustomerName('');
              }}
            >
              İptal
            </Button>
            <Button 
              onClick={createQuickQuote}
              disabled={!quickQuoteCustomerName.trim()}
              className="bg-blue-600 hover:bg-blue-700"
            >
              <FileText className="w-4 h-4 mr-2" />
              Teklif Oluştur
            </Button>
          </DialogFooter>
        </DialogContent>
      </Dialog>
    </div>
  );
}

export default App;