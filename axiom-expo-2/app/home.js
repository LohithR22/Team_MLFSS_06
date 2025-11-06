import React, { useState, useEffect } from 'react';
import { View, Text, StyleSheet, Button, Image, Alert, ActivityIndicator, Platform, ScrollView, TouchableOpacity, Linking } from 'react-native';
import * as ImagePicker from 'expo-image-picker';
import * as Location from 'expo-location';

// Conditional WebView import
let WebView;
if (Platform.OS === 'web') {
  // For web, we'll use an iframe approach
  WebView = null;
} else {
  try {
    WebView = require('react-native-webview').WebView;
  } catch (e) {
    WebView = null;
  }
}

const HomeScreen = () => {
  const [location, setLocation] = useState(null);
  const [errorMsg, setErrorMsg] = useState(null);
  const [imageUri, setImageUri] = useState(null);
  const [uploading, setUploading] = useState(false);
  const [medicines, setMedicines] = useState(null);
  const [scraping, setScraping] = useState(false);
  const [scrapeResults, setScrapeResults] = useState(null);
  const [mapHtml, setMapHtml] = useState(null);
  const [loadingMap, setLoadingMap] = useState(false);
  const [pharmacyResults, setPharmacyResults] = useState(null);
  const [hwcReport, setHwcReport] = useState(null);
  const [loadingHwc, setLoadingHwc] = useState(false);

  useEffect(() => {
    (async () => {
      let { status } = await Location.requestForegroundPermissionsAsync();
      if (status !== 'granted') {
        setErrorMsg('Permission to access location was denied');
        return;
      }

      let location = await Location.getCurrentPositionAsync({});
      setLocation(location.coords);
    })();
    
    // Load HWC Report
    loadHwcReport();
  }, []);

  const loadHwcReport = async () => {
    try {
      setLoadingHwc(true);
      const response = await fetch('http://localhost:3000/hwc-report');
      if (!response.ok) {
        throw new Error('Failed to load HWC report');
      }
      const data = await response.json();
      setHwcReport(data);
    } catch (err) {
      console.error('Error loading HWC report:', err);
    } finally {
      setLoadingHwc(false);
    }
  };

  const pickImage = async () => {
    const { status } = await ImagePicker.requestMediaLibraryPermissionsAsync();
    if (status !== 'granted') {
      Alert.alert('Permission required', 'We need access to your photos to upload a prescription.');
      return;
    }

    const result = await ImagePicker.launchImageLibraryAsync({
      mediaTypes: 'images',
      allowsEditing: false,
      quality: 1,
    });

    if (!result.canceled && result.assets && result.assets.length > 0) {
      setImageUri(result.assets[0].uri);
      setMedicines(null);
    }
  };

  const uploadImage = async () => {
    if (!imageUri) {
      Alert.alert('No image', 'Please select an image first.');
      return;
    }
    try {
      setUploading(true);
      const uri = imageUri;
      const fileName = uri.split('/').pop() || 'prescription.jpg';
      const match = /\.(\w+)$/.exec(fileName);
      const type = match ? `image/${match[1]}` : 'image/jpeg';

      const formData = new FormData();
      if (Platform.OS === 'web') {
        const res = await fetch(uri);
        const blob = await res.blob();
        formData.append('image', blob, fileName);
      } else {
        formData.append('image', {
          uri,
          name: fileName,
          type,
        });
      }

      const response = await fetch('http://localhost:3000/ocr/upload', {
        method: 'POST',
        body: formData,
      });

      const data = await response.json();
      if (!response.ok) {
        const detail = data?.details || data?.stderr || data?.stdout;
        throw new Error((data?.error ? `${data.error}${detail ? `: ${detail}` : ''}` : null) || 'Upload failed');
      }
      const meds = data.medicines || [];
      setMedicines(meds);
      // Trigger scraping
      if (meds.length) {
        try {
          setScraping(true);
          const resp = await fetch('http://localhost:3000/scrape', {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({ medicines: meds })
          });
          const scrape = await resp.json();
          if (!resp.ok) throw new Error(scrape?.error || 'Scrape failed');
          setScrapeResults(scrape.results || []);
          
          // Find pharmacies and generate delivery map
          if (location && meds.length > 0) {
            try {
              setLoadingMap(true);
              
              // Step 1: Find top pharmacies based on user location and medicines
              const pharmacyResponse = await fetch('http://localhost:3000/find-pharmacies', {
                method: 'POST',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify({
                  source_lat: location.latitude,
                  source_lon: location.longitude,
                  medicine_names: meds,
                  top_k: 5
                })
              });
              
              const pharmacyData = await pharmacyResponse.json();
              if (!pharmacyResponse.ok) {
                throw new Error(pharmacyData?.error || 'Failed to find pharmacies');
              }
              
              // Store pharmacy results for display
              setPharmacyResults(pharmacyData);
              
              // Step 2: Categorize stores based on medicine availability
              // Green: All medicines available (no missing, no alternatives)
              // Yellow: Some alternatives but no missing
              // Red: Some medicines missing
              const greenStores = [];
              const yellowStores = [];
              const redStores = [];
              
              const rankedStores = pharmacyData.ranked_stores || [];
              rankedStores.forEach(store => {
                const status = store.medicine_status || {};
                const missing = status.missing || [];
                const alternatives = status.alternative || [];
                
                const coords = [store.latitude, store.longitude];
                
                if (missing.length > 0) {
                  // Some medicines missing - mark as red
                  redStores.push(coords);
                } else if (alternatives.length > 0) {
                  // Has alternatives but no missing - mark as yellow
                  yellowStores.push(coords);
                } else {
                  // All available - mark as green
                  greenStores.push(coords);
                }
              });
              
              // Step 3: Generate delivery map with categorized stores
              const mapResponse = await fetch('http://localhost:3000/delivery-map', {
                method: 'POST',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify({
                  origin: { latitude: location.latitude, longitude: location.longitude },
                  green_stores: greenStores,
                  yellow_stores: yellowStores,
                  red_stores: redStores
                })
              });
              
              const mapData = await mapResponse.json();
              if (mapResponse.ok && mapData.map_html) {
                setMapHtml(mapData.map_html);
              } else {
                console.error('Map generation error:', mapData.error);
              }
            } catch (err) {
              console.error('Failed to generate map:', err);
            } finally {
              setLoadingMap(false);
            }
          }
        } catch (err) {
          Alert.alert('Scrape Error', err?.message || 'Failed to scrape');
        } finally {
          setScraping(false);
        }
      } else {
        setScrapeResults([]);
      }
      Alert.alert('Success', 'OCR completed.');
    } catch (e) {
      Alert.alert('Error', e?.message || 'Failed to upload');
    } finally {
      setUploading(false);
    }
  };

  return (
    <ScrollView contentContainerStyle={styles.container}>
      <Text style={styles.title}>Welcome Home!</Text>
      {location ? (
        <View>
          <Text>Latitude: {location.latitude}</Text>
          <Text>Longitude: {location.longitude}</Text>
        </View>
      ) : (
        <Text>{errorMsg || 'Fetching location...'}</Text>
      )}
      <View style={{ height: 24 }} />
      {imageUri ? (
        <Image source={{ uri: imageUri }} style={styles.preview} resizeMode="cover" />
      ) : (
        <View style={styles.placeholder}><Text>No image selected</Text></View>
      )}
      <View style={{ height: 12 }} />
      <View style={styles.actions}>
        <Button title="Pick Image" onPress={pickImage} />
        <View style={{ height: 12 }} />
        <Button title="Upload & Extract" onPress={uploadImage} disabled={!imageUri || uploading} />
      </View>
      {uploading && <ActivityIndicator style={{ marginTop: 16 }} />}
      {scraping && <ActivityIndicator style={{ marginTop: 8 }} />}
      {medicines && (
        <View style={{ marginTop: 24, width: '100%', paddingHorizontal: 24 }}>
          <Text style={styles.subtitle}>Extracted Medicines</Text>
          {medicines.length === 0 ? (
            <Text>None detected.</Text>
          ) : (
            medicines.map((m, idx) => (
              <Text key={`${m}-${idx}`}>• {m}</Text>
            ))
          )}
        </View>
      )}
      {scrapeResults && (
        <View style={{ marginTop: 16, width: '100%', paddingHorizontal: 24 }}>
          <Text style={styles.subtitle}>Scrape Results (Apollo & Netmed)</Text>
          {scrapeResults.length === 0 ? (
            <Text>None.</Text>
          ) : (
            scrapeResults.map((r, idx) => (
              <View key={`scr-${idx}`} style={{ marginBottom: 12 }}>
                <Text style={{ fontWeight: '600' }}>{r.medicine}</Text>
                {r.apollo?.best_choice && (
                  <Text>Apollo best: {r.apollo.best_choice.name} - {r.apollo.best_choice.price}</Text>
                )}
                {r.netmed?.best_choice && (
                  <Text>Netmed best: {r.netmed.best_choice.name} - {r.netmed.best_choice.price}</Text>
                )}
              </View>
            ))
          )}
        </View>
      )}
      {pharmacyResults && (
        <View style={{ marginTop: 16, width: '100%', paddingHorizontal: 24 }}>
          <Text style={styles.subtitle}>Top Pharmacies Found</Text>
          {pharmacyResults.ranked_stores && pharmacyResults.ranked_stores.length === 0 ? (
            <Text>No pharmacies found.</Text>
          ) : (
            pharmacyResults.ranked_stores?.map((store, idx) => (
              <View key={`pharm-${idx}`} style={{ marginBottom: 12, padding: 8, backgroundColor: '#f5f5f5', borderRadius: 4 }}>
                <Text style={{ fontWeight: '600' }}>{idx + 1}. {store.store_name}</Text>
                <Text>Distance: {store.distance_from_source?.toFixed(2)} km</Text>
                <Text>Total Price: ₹{store.total_price?.toFixed(2) || 'N/A'}</Text>
                {store.medicine_status?.available?.length > 0 && (
                  <Text style={{ color: 'green' }}>✓ Available: {store.medicine_status.available.join(', ')}</Text>
                )}
                {store.medicine_status?.alternative?.length > 0 && (
                  <Text style={{ color: 'orange' }}>⚠ Alternatives: {store.medicine_status.alternative.map(a => a.found).join(', ')}</Text>
                )}
                {store.medicine_status?.missing?.length > 0 && (
                  <Text style={{ color: 'red' }}>✗ Missing: {store.medicine_status.missing.join(', ')}</Text>
                )}
              </View>
            ))
          )}
        </View>
      )}
      {loadingMap && <ActivityIndicator style={{ marginTop: 16 }} />}
      {mapHtml && (
        <View style={{ marginTop: 24, width: '100%', height: 400, paddingHorizontal: 24 }}>
          <Text style={styles.subtitle}>Delivery Map</Text>
          {Platform.OS === 'web' ? (
            <View style={{ flex: 1, marginTop: 8 }}>
              {/* For web, we'll create an iframe or use a web component */}
              <iframe
                srcDoc={mapHtml}
                style={{ width: '100%', height: '100%', border: 'none' }}
                title="Delivery Map"
                sandbox="allow-scripts allow-same-origin allow-popups allow-popups-to-escape-sandbox"
              />
            </View>
          ) : WebView ? (
            <WebView
              source={{ html: mapHtml }}
              style={{ flex: 1, marginTop: 8 }}
              javaScriptEnabled={true}
              domStorageEnabled={true}
            />
          ) : (
            <Text>WebView not available. Please install react-native-webview</Text>
          )}
        </View>
      )}

      {/* HWC Report Section */}
      <View style={{ marginTop: 48, width: '100%', paddingHorizontal: 24 }}>
        <Text style={styles.sectionTitle}>Health & Wellness Centres Report</Text>
        {loadingHwc ? (
          <ActivityIndicator style={{ marginTop: 16 }} />
        ) : hwcReport ? (
          <>
            {/* Service Packages - First Two Cards Side by Side */}
            {hwcReport.service_packages && (
              <View style={{ marginTop: 16 }}>
                <Text style={styles.subtitle}>{hwcReport.service_packages.title}</Text>
                <Text style={styles.description}>{hwcReport.service_packages.description}</Text>
                <View style={styles.cardsRow}>
                  {hwcReport.service_packages.cards && hwcReport.service_packages.cards.slice(0, 2).map((card, idx) => (
                    <View key={card.id || idx} style={[styles.card, idx === 0 && styles.cardFirst]}>
                      <Text style={styles.cardIcon}>{card.icon || '📋'}</Text>
                      <Text style={styles.cardTitle}>{card.title}</Text>
                      {card.details && (
                        <View style={{ marginTop: 8 }}>
                          {card.details.map((detail, dIdx) => (
                            <View key={dIdx} style={{ marginBottom: 4 }}>
                              <Text style={styles.detailLevel}>{detail.level}</Text>
                              <Text style={styles.detailCount}>{detail.count}</Text>
                            </View>
                          ))}
                        </View>
                      )}
                      {card.description && (
                        <Text style={styles.cardDescription}>{card.description}</Text>
                      )}
                    </View>
                  ))}
                </View>
                {/* Third card if exists - show full width */}
                {hwcReport.service_packages.cards && hwcReport.service_packages.cards.length > 2 && (
                  <View style={[styles.card, styles.cardFullWidth]}>
                    <Text style={styles.cardIcon}>{hwcReport.service_packages.cards[2].icon || '📋'}</Text>
                    <Text style={styles.cardTitle}>{hwcReport.service_packages.cards[2].title}</Text>
                    {hwcReport.service_packages.cards[2].services && (
                      <View style={{ marginTop: 8 }}>
                        {hwcReport.service_packages.cards[2].services.map((service, sIdx) => (
                          <Text key={service.id || sIdx} style={styles.serviceItem}>• {service.name}</Text>
                        ))}
                      </View>
                    )}
                  </View>
                )}
              </View>
            )}

            {/* State Wise Data - Scrollable */}
            {hwcReport.state_wise_data && (
              <View style={{ marginTop: 32 }}>
                <Text style={styles.subtitle}>State-wise Operational HWC Data</Text>
                <ScrollView 
                  style={styles.stateScrollView}
                  nestedScrollEnabled={true}
                >
                  {hwcReport.state_wise_data.map((state, idx) => (
                    <View key={idx} style={styles.stateRow}>
                      <Text style={styles.stateName}>{state.state}</Text>
                      <Text style={styles.stateCount}>{state.operational_hwcs.toLocaleString()} HWCs</Text>
                    </View>
                  ))}
                </ScrollView>
              </View>
            )}

            {/* Official Links */}
            {hwcReport.official_links && (
              <View style={{ marginTop: 32, marginBottom: 32 }}>
                <Text style={styles.subtitle}>Official Links</Text>
                {hwcReport.official_links.map((link, idx) => (
                  <TouchableOpacity
                    key={idx}
                    style={styles.linkCard}
                    onPress={() => Linking.openURL(link.url)}
                  >
                    <Text style={styles.linkTitle}>{link.title}</Text>
                    <Text style={styles.linkDescription}>{link.description}</Text>
                    <Text style={styles.linkUrl}>{link.url}</Text>
                  </TouchableOpacity>
                ))}
              </View>
            )}
          </>
        ) : (
          <Text style={{ marginTop: 16, color: '#666' }}>No HWC report data available</Text>
        )}
      </View>
    </ScrollView>
  );
};

const styles = StyleSheet.create({
  container: {
    flexGrow: 1,
    alignItems: 'center',
    paddingTop: 48,
    paddingBottom: 48,
  },
  title: {
    fontSize: 24,
    fontWeight: 'bold',
    marginBottom: 20,
  },
  preview: {
    width: 280,
    height: 280,
    borderRadius: 8,
    backgroundColor: '#eee',
  },
  placeholder: {
    width: 280,
    height: 280,
    borderRadius: 8,
    backgroundColor: '#f0f0f0',
    alignItems: 'center',
    justifyContent: 'center',
  },
  actions: {
    width: 200,
  },
  subtitle: {
    fontSize: 18,
    fontWeight: '600',
    marginBottom: 8,
  },
  sectionTitle: {
    fontSize: 22,
    fontWeight: 'bold',
    marginBottom: 8,
    color: '#333',
  },
  description: {
    fontSize: 14,
    color: '#666',
    marginBottom: 16,
    lineHeight: 20,
  },
  cardsRow: {
    flexDirection: 'row',
    flexWrap: 'wrap',
    justifyContent: 'space-between',
  },
  card: {
    flex: 1,
    backgroundColor: '#f8f9fa',
    borderRadius: 12,
    padding: 16,
    marginBottom: 12,
    marginLeft: 4,
    marginRight: 4,
    borderWidth: 1,
    borderColor: '#e0e0e0',
  },
  cardFirst: {
    marginLeft: 0,
  },
  cardFullWidth: {
    marginLeft: 0,
    marginRight: 0,
  },
  cardIcon: {
    fontSize: 32,
    marginBottom: 8,
  },
  cardTitle: {
    fontSize: 16,
    fontWeight: '600',
    marginBottom: 8,
    color: '#333',
  },
  cardDescription: {
    fontSize: 14,
    color: '#666',
    marginTop: 8,
    lineHeight: 20,
  },
  detailLevel: {
    fontSize: 13,
    fontWeight: '600',
    color: '#444',
  },
  detailCount: {
    fontSize: 12,
    color: '#666',
    marginTop: 2,
  },
  serviceItem: {
    fontSize: 13,
    color: '#555',
    marginBottom: 6,
    lineHeight: 18,
  },
  stateScrollView: {
    maxHeight: 400,
    backgroundColor: '#f8f9fa',
    borderRadius: 8,
    padding: 12,
    borderWidth: 1,
    borderColor: '#e0e0e0',
  },
  stateRow: {
    flexDirection: 'row',
    justifyContent: 'space-between',
    alignItems: 'center',
    paddingVertical: 10,
    paddingHorizontal: 12,
    borderBottomWidth: 1,
    borderBottomColor: '#e0e0e0',
  },
  stateName: {
    fontSize: 15,
    fontWeight: '500',
    color: '#333',
    flex: 1,
  },
  stateCount: {
    fontSize: 15,
    fontWeight: '600',
    color: '#2196F3',
  },
  linkCard: {
    backgroundColor: '#f8f9fa',
    borderRadius: 8,
    padding: 16,
    marginBottom: 12,
    borderWidth: 1,
    borderColor: '#e0e0e0',
  },
  linkTitle: {
    fontSize: 16,
    fontWeight: '600',
    color: '#2196F3',
    marginBottom: 4,
  },
  linkDescription: {
    fontSize: 14,
    color: '#666',
    marginBottom: 8,
    lineHeight: 20,
  },
  linkUrl: {
    fontSize: 12,
    color: '#999',
    fontStyle: 'italic',
  },
});

export default HomeScreen;
