import { Ionicons } from '@expo/vector-icons';
import AsyncStorage from '@react-native-async-storage/async-storage';
import * as Location from 'expo-location';
import { useFocusEffect, useRouter } from 'expo-router';
import { StatusBar } from 'expo-status-bar';
import React, { useEffect, useState } from 'react';
import {
  ActivityIndicator,
  Alert,
  Modal,
  Platform,
  ScrollView,
  StyleSheet,
  Text,
  TouchableOpacity,
  View
} from 'react-native';
import { SafeAreaView } from 'react-native-safe-area-context';
import Card from '../../components/Card';
import GradientButton from '../../components/GradientButton';
import { theme } from '../../constants/theme';

// Conditional WebView import
let WebView;
if (Platform.OS === 'web') {
  WebView = null;
} else {
  try {
    WebView = require('react-native-webview').WebView;
  } catch (e) {
    WebView = null;
  }
}

const PharmaciesScreen = () => {
  const router = useRouter();
  const [location, setLocation] = useState(null);
  const [loadingMap, setLoadingMap] = useState(false);
  const [pharmacyResults, setPharmacyResults] = useState(null);
  const [mapHtml, setMapHtml] = useState(null);
  const [medicines, setMedicines] = useState([]);
  const [deliveryAssigned, setDeliveryAssigned] = useState(false);
  const [deliveryAgent, setDeliveryAgent] = useState(null);
  const [showStoreModal, setShowStoreModal] = useState(false);
  const [selectedStore, setSelectedStore] = useState(null);
  const [janaushadhiData, setJanaushadhiData] = useState(null);
  const [loadingJanaushadhi, setLoadingJanaushadhi] = useState(false);

  // Load medicines function
  const loadMedicines = React.useCallback(async () => {
    try {
      let savedMedicines = null;

      // Try AsyncStorage first
      try {
        savedMedicines = await AsyncStorage.getItem('extractedMedicines');
      } catch (e) {
        console.warn('AsyncStorage getItem failed, trying localStorage:', e);
      }

      // On web, also try localStorage as fallback
      if (!savedMedicines && Platform.OS === 'web') {
        try {
          savedMedicines = localStorage.getItem('extractedMedicines');
        } catch (e) {
          console.warn('localStorage getItem failed:', e);
        }
      }

      if (savedMedicines) {
        const parsed = JSON.parse(savedMedicines);
        setMedicines(Array.isArray(parsed) ? parsed : []);
        console.log('✅ Medicines loaded from storage:', parsed);
      } else {
        setMedicines([]);
        console.log('ℹ️ No medicines found in storage');
      }
    } catch (e) {
      console.error('❌ Failed to load medicines from storage:', e);
      setMedicines([]);
    }
  }, []);

  useEffect(() => {
    (async () => {
      let { status } = await Location.requestForegroundPermissionsAsync();
      if (status !== 'granted') {
        Alert.alert('Location Permission', 'Location access is needed for finding pharmacies.');
        return;
      }
      let location = await Location.getCurrentPositionAsync({});
      setLocation(location.coords);
    })();

    // Load medicines on initial mount
    loadMedicines();
  }, [loadMedicines]);

  // Reload medicines when screen comes into focus
  useFocusEffect(
    React.useCallback(() => {
      loadMedicines();
    }, [loadMedicines])
  );

  const findPharmacies = async () => {
    if (!location) {
      Alert.alert('Error', 'Location not available. Please enable location services.');
      return;
    }
    if (medicines.length === 0) {
      Alert.alert('Info', 'Please go to Prescription tab to extract medicines first.');
      return;
    }

    try {
      setLoadingMap(true);

      // Step 1: Find top pharmacies
      const pharmacyResponse = await fetch('http://localhost:3000/find-pharmacies', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({
          source_lat: location.latitude,
          source_lon: location.longitude,
          medicine_names: medicines,
          top_k: 5,
        }),
      });

      const pharmacyData = await pharmacyResponse.json();
      if (!pharmacyResponse.ok) {
        throw new Error(pharmacyData?.error || 'Failed to find pharmacies');
      }

      setPharmacyResults(pharmacyData);

      // Step 2: Generate delivery map with proper color coding
      // Reference implementation: green = all available, yellow = has alternatives, red = some missing
      const greenStores = [];
      const yellowStores = [];
      const redStores = [];

      const rankedStores = pharmacyData.ranked_stores || [];
      rankedStores.forEach((store, idx) => {
        const status = store.medicine_status || {};

        // Get lists and ensure no duplicates (safeguard against conflicts)
        const available = (status.available || []).filter((med, idx, arr) => arr.indexOf(med) === idx);
        const alternatives = (status.alternative || []).filter((alt, idx, arr) => {
          // For alternatives, check both requested and found names
          const reqName = typeof alt === 'string' ? alt : alt.requested;
          return arr.findIndex(a => {
            const aReq = typeof a === 'string' ? a : a.requested;
            return aReq === reqName;
          }) === idx;
        });
        const missing = (status.missing || []).filter((med, idx, arr) => arr.indexOf(med) === idx);

        // Remove medicines from available/alternatives if they appear in missing (shouldn't happen, but safeguard)
        const availableFiltered = available.filter(med => !missing.includes(med));
        const alternativesFiltered = alternatives.filter(alt => {
          const reqName = typeof alt === 'string' ? alt : alt.requested;
          return !missing.includes(reqName);
        });

        // Remove medicines from alternatives if they appear in available (exact match takes priority)
        const alternativesFinal = alternativesFiltered.filter(alt => {
          const reqName = typeof alt === 'string' ? alt : alt.requested;
          return !availableFiltered.includes(reqName);
        });

        const coords = [store.latitude, store.longitude];

        // Color coding logic:
        // - First pharmacy (idx === 0): Always GREEN (highest priority)
        // - RED: Some medicines are missing (for other pharmacies)
        // - YELLOW: Has alternatives or not all available (for other pharmacies)
        // - GREEN: All medicines available (for other pharmacies, but first is always green)

        if (idx === 0) {
          // First pharmacy is always green
          greenStores.push(coords);
        } else {
          // For other pharmacies, use normal logic
          if (missing.length > 0) {
            redStores.push(coords);
          } else {
            // No missing medicines - mark as yellow (alternatives or partial availability)
            yellowStores.push(coords);
          }
        }
      });

      const mapResponse = await fetch('http://localhost:3000/delivery-map', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({
          origin: { latitude: location.latitude, longitude: location.longitude },
          green_stores: greenStores,
          yellow_stores: yellowStores,
          red_stores: redStores,
        }),
      });

      const mapData = await mapResponse.json();
      if (mapResponse.ok && mapData.map_html) {
        setMapHtml(mapData.map_html);
        setDeliveryAssigned(false); // Reset delivery status when new map is generated
        setDeliveryAgent(null);

        // Fetch Jan Aushadhi data after map is generated
        if (medicines.length > 0) {
          fetchJanaushadhiData();
        }
      }
    } catch (err) {
      Alert.alert('Error', err?.message || 'Failed to find pharmacies');
    } finally {
      setLoadingMap(false);
    }
  };

  // Fetch Jan Aushadhi data
  const fetchJanaushadhiData = async () => {
    if (medicines.length === 0) return;

    setLoadingJanaushadhi(true);
    try {
      const medicineNames = medicines.map(m => typeof m === 'string' ? m : m.name || m.medicine || '');

      const response = await fetch('http://localhost:3000/janaushadhi-lookup', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ medicine_names: medicineNames }),
      });

      const data = await response.json();
      if (response.ok) {
        setJanaushadhiData(data);
      } else {
        console.error('Jan Aushadhi lookup error:', data.error);
      }
    } catch (err) {
      console.error('Failed to fetch Jan Aushadhi data:', err);
    } finally {
      setLoadingJanaushadhi(false);
    }
  };

  // Calculate haversine distance between two coordinates
  const haversineDistance = (lat1, lon1, lat2, lon2) => {
    const R = 6371000; // Earth radius in meters
    const dLat = (lat2 - lat1) * Math.PI / 180;
    const dLon = (lon2 - lon1) * Math.PI / 180;
    const a =
      Math.sin(dLat / 2) * Math.sin(dLat / 2) +
      Math.cos(lat1 * Math.PI / 180) * Math.cos(lat2 * Math.PI / 180) *
      Math.sin(dLon / 2) * Math.sin(dLon / 2);
    const c = 2 * Math.atan2(Math.sqrt(a), Math.sqrt(1 - a));
    return R * c; // Distance in meters
  };

  // Find closest agent to a store
  const findClosestAgent = (storeLat, storeLon) => {
    // Hardcoded agent coordinates from delivery_map.py
    const agents = [
      { idx: 0, lat: 12.9650, lon: 77.6000 },
      { idx: 1, lat: 12.9800, lon: 77.5900 },
      { idx: 2, lat: 12.9550, lon: 77.6050 },
      { idx: 3, lat: 12.9750, lon: 77.6100 },
      { idx: 4, lat: 12.9900, lon: 77.5800 }
    ];

    let closestAgent = agents[0];
    let minDistance = haversineDistance(storeLat, storeLon, agents[0].lat, agents[0].lon);

    agents.forEach((agent) => {
      const distance = haversineDistance(storeLat, storeLon, agent.lat, agent.lon);
      if (distance < minDistance) {
        minDistance = distance;
        closestAgent = agent;
      }
    });

    return closestAgent.idx;
  };

  const requestDelivery = () => {
    if (!location) {
      Alert.alert('Error', 'Location not available.');
      return;
    }
    if (!pharmacyResults || !pharmacyResults.ranked_stores || pharmacyResults.ranked_stores.length === 0) {
      Alert.alert('Error', 'No pharmacies found. Please search for pharmacies first.');
      return;
    }

    // Show store selection modal
    setShowStoreModal(true);
  };

  const assignDeliveryToStore = async (store) => {
    if (!location) {
      Alert.alert('Error', 'Location not available.');
      return;
    }

    try {
      setLoadingMap(true);
      setShowStoreModal(false);
      setSelectedStore(store);

      // Find closest agent to selected store
      const closestAgentIdx = findClosestAgent(store.latitude, store.longitude);

      // Re-categorize stores for map
      const greenStores = [];
      const yellowStores = [];
      const redStores = [];

      pharmacyResults.ranked_stores.forEach((storeItem, idx) => {
        const status = storeItem.medicine_status || {};
        const missing = (status.missing || []).filter((med, idx, arr) => arr.indexOf(med) === idx);
        const alternatives = (status.alternative || []).filter((alt, idx, arr) => {
          const reqName = typeof alt === 'string' ? alt : alt.requested;
          return arr.findIndex(a => {
            const aReq = typeof a === 'string' ? a : a.requested;
            return aReq === reqName;
          }) === idx;
        });
        const available = (status.available || []).filter((med, idx, arr) => arr.indexOf(med) === idx);

        const availableFiltered = available.filter(med => !missing.includes(med));
        const alternativesFiltered = alternatives.filter(alt => {
          const reqName = typeof alt === 'string' ? alt : alt.requested;
          return !missing.includes(reqName);
        });
        const alternativesFinal = alternativesFiltered.filter(alt => {
          const reqName = typeof alt === 'string' ? alt : alt.requested;
          return !availableFiltered.includes(reqName);
        });

        const coords = [storeItem.latitude, storeItem.longitude];

        if (idx === 0) {
          greenStores.push(coords);
        } else {
          if (missing.length > 0) {
            redStores.push(coords);
          } else {
            yellowStores.push(coords);
          }
        }
      });

      // Request map with delivery assignment
      const mapResponse = await fetch('http://localhost:3000/delivery-map', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({
          origin: { latitude: location.latitude, longitude: location.longitude },
          green_stores: greenStores,
          yellow_stores: yellowStores,
          red_stores: redStores,
          best_store: { latitude: store.latitude, longitude: store.longitude },
          create_delivery: true,
          agent_idx: closestAgentIdx,
        }),
      });

      const mapData = await mapResponse.json();
      console.log('📦 Map response received');
      console.log('📦 Map HTML length:', mapData.map_html?.length || 0);
      console.log('📋 Assignments count:', mapData.assignments?.length || 0);
      console.log('📋 Assignments:', JSON.stringify(mapData.assignments, null, 2));

      if (mapResponse.ok && mapData.map_html) {
        // Force map update by clearing first, then setting new HTML
        setMapHtml(null);
        setTimeout(() => {
          setMapHtml(mapData.map_html);
          setDeliveryAssigned(true);
        }, 100);

        // Extract agent info from assignments
        if (mapData.assignments && mapData.assignments.length > 0) {
          const assignment = mapData.assignments[0];
          console.log('👤 Assignment:', assignment);
          console.log('👤 Agent Profile:', assignment.agent_profile);

          if (assignment.agent_profile) {
            // Store full assignment data for display
            setDeliveryAgent({
              ...assignment.agent_profile,
              assignment: assignment // Store full assignment for distance/price details
            });

            // Format distance and price info
            const leg1Km = assignment.dist1_m ? (assignment.dist1_m / 1000).toFixed(3) : 'N/A';
            const leg2Km = assignment.dist2_m ? (assignment.dist2_m / 1000).toFixed(3) : 'N/A';
            const totalKm = assignment.total_m ? (assignment.total_m / 1000).toFixed(3) : 'N/A';
            const charge = assignment.charge || 'N/A';

            Alert.alert(
              'Delivery Assigned!',
              `Store: ${store.store_name}\nAgent: ${assignment.agent_profile.name}\nPhone: ${assignment.agent_profile.phone}\nVehicle: ${assignment.agent_profile.vehicle}\n\nDistance:\n• Agent → Store: ${leg1Km} km\n• Store → You: ${leg2Km} km\n• Total: ${totalKm} km\n\nDelivery Charge: ₹${charge}\n\nDelivery route has been added to the map.`,
              [{ text: 'OK' }]
            );
          } else {
            console.error('❌ No agent_profile in assignment');
            Alert.alert('Warning', 'Delivery assigned but agent details not available.');
          }
        } else {
          console.warn('⚠️ No assignments in response');
          Alert.alert('Warning', 'Delivery route created but assignment details not available. Check console for details.');
        }
      } else {
        throw new Error(mapData?.error || 'Failed to create delivery assignment');
      }
    } catch (err) {
      Alert.alert('Error', err?.message || 'Failed to assign delivery');
    } finally {
      setLoadingMap(false);
    }
  };

  return (
    <SafeAreaView style={styles.container} edges={['top']}>
      <StatusBar style="dark" />
      <ScrollView
        style={styles.scrollView}
        contentContainerStyle={styles.scrollContent}
        showsVerticalScrollIndicator={false}
      >
        {/* Header */}
        <View style={styles.header}>
          <Text style={styles.title}>Offline Pharmacies</Text>
          <Text style={styles.subtitle}>
            Discover nearby pharmacies with your required medicines
          </Text>
        </View>

        {/* Location Status */}
        <Card style={styles.locationCard}>
          <View style={styles.locationRow}>
            <Ionicons
              name={location ? 'location' : 'location-outline'}
              size={24}
              color={location ? theme.colors.success : theme.colors.textLight}
            />
            <View style={styles.locationInfo}>
              <Text style={styles.locationLabel}>Your Location</Text>
              <Text style={styles.locationText}>
                {location
                  ? `${location.latitude.toFixed(4)}, ${location.longitude.toFixed(4)}`
                  : 'Getting location...'}
              </Text>
            </View>
          </View>
        </Card>

        {/* Medicines Display */}
        {medicines.length > 0 && (
          <Card style={styles.medicinesCard}>
            <View style={styles.resultsHeader}>
              <Ionicons name="pills" size={24} color={theme.colors.primary} style={{ marginRight: theme.spacing.sm }} />
              <Text style={styles.resultsTitle}>Medicines to Find</Text>
              <TouchableOpacity
                onPress={loadMedicines}
                style={styles.refreshButton}
                activeOpacity={0.7}
              >
                <Ionicons name="refresh" size={20} color={theme.colors.primary} />
              </TouchableOpacity>
            </View>
            <View style={styles.medicinesList}>
              {medicines.map((medicine, idx) => (
                <View key={idx} style={[styles.medicineBadge, { margin: theme.spacing.xs }]}>
                  <Text style={styles.medicineBadgeText}>{medicine}</Text>
                </View>
              ))}
            </View>
            <Text style={styles.medicineCount}>
              {medicines.length} medicine{medicines.length !== 1 ? 's' : ''} ready to search
            </Text>
          </Card>
        )}

        {/* Info Card */}
        {medicines.length === 0 && (
          <Card style={styles.infoCard}>
            <Ionicons name="information-circle" size={24} color={theme.colors.info} />
            <Text style={styles.infoText}>
              Extract medicines from your prescription first to find nearby pharmacies.
            </Text>
            <GradientButton
              title="Go to Prescription"
              onPress={() => router.push('/(tabs)/prescription')}
              variant="secondary"
              style={styles.infoButton}
            />
          </Card>
        )}

        {/* Find Pharmacies Button */}
        {medicines.length > 0 && (
          <GradientButton
            title={loadingMap ? 'Searching...' : `Find Pharmacies for ${medicines.length} Medicine${medicines.length !== 1 ? 's' : ''}`}
            onPress={findPharmacies}
            disabled={loadingMap || !location}
            loading={loadingMap}
            style={styles.findButton}
          />
        )}

        {/* Pharmacy Results */}
        {pharmacyResults && pharmacyResults.ranked_stores && (
          <Card style={styles.resultsCard}>
            <View style={styles.resultsHeader}>
              <Ionicons name="storefront" size={24} color={theme.colors.primary} style={{ marginRight: theme.spacing.sm }} />
              <Text style={styles.resultsTitle}>Nearby Pharmacies</Text>
            </View>
            {pharmacyResults.ranked_stores.map((store, idx) => {
              const status = store.medicine_status || {};

              // Deduplicate and filter medicines to avoid conflicts (same logic as map generation)
              const available = (status.available || []).filter((med, idx, arr) => arr.indexOf(med) === idx);
              const alternatives = (status.alternative || []).filter((alt, idx, arr) => {
                const reqName = typeof alt === 'string' ? alt : alt.requested;
                return arr.findIndex(a => {
                  const aReq = typeof a === 'string' ? a : a.requested;
                  return aReq === reqName;
                }) === idx;
              });
              const missing = (status.missing || []).filter((med, idx, arr) => arr.indexOf(med) === idx);

              // Remove conflicts: if a medicine is in missing, remove from available/alternatives
              const availableFiltered = available.filter(med => !missing.includes(med));
              const alternativesFiltered = alternatives.filter(alt => {
                const reqName = typeof alt === 'string' ? alt : alt.requested;
                return !missing.includes(reqName);
              });

              // Remove conflicts: if a medicine is in available, remove from alternatives (exact match takes priority)
              const alternativesFinal = alternativesFiltered.filter(alt => {
                const reqName = typeof alt === 'string' ? alt : alt.requested;
                return !availableFiltered.includes(reqName);
              });

              // Determine color based on final filtered status:
              // - First pharmacy (idx === 0): Always GREEN
              // - Other pharmacies: RED if missing, YELLOW otherwise
              const statusColor =
                idx === 0
                  ? theme.colors.success  // First pharmacy is always GREEN
                  : missing.length > 0
                    ? theme.colors.error  // RED if missing medicines
                    : theme.colors.warning;  // YELLOW for others (alternatives or partial availability)

              return (
                <View key={idx} style={styles.pharmacyItem}>
                  <View style={styles.pharmacyHeader}>
                    <View style={styles.pharmacyRank}>
                      <Text style={styles.rankNumber}>{idx + 1}</Text>
                    </View>
                    <View style={styles.pharmacyInfo}>
                      <Text style={styles.pharmacyName}>{store.store_name}</Text>
                      <Text style={styles.pharmacyDistance}>
                        {store.distance_from_source?.toFixed(2)} km away
                      </Text>
                    </View>
                    <View style={[styles.statusBadge, { backgroundColor: `${statusColor}20` }]}>
                      <View style={[styles.statusDot, { backgroundColor: statusColor }]} />
                    </View>
                  </View>
                  <Text style={styles.pharmacyPrice}>
                    Total: ₹{store.total_price?.toFixed(2) || 'N/A'}
                  </Text>
                  {availableFiltered.length > 0 && (
                    <View style={styles.statusRow}>
                      <Ionicons name="checkmark-circle" size={16} color={theme.colors.success} style={{ marginRight: theme.spacing.xs }} />
                      <Text style={styles.statusText}>
                        Available: {availableFiltered.join(', ')}
                      </Text>
                    </View>
                  )}
                  {alternativesFinal.length > 0 && (
                    <View style={styles.statusRow}>
                      <Ionicons name="swap-horizontal" size={16} color={theme.colors.warning} style={{ marginRight: theme.spacing.xs }} />
                      <Text style={styles.statusText}>
                        Alternatives: {alternativesFinal.map((a) => typeof a === 'string' ? a : a.found || a.requested).join(', ')}
                      </Text>
                    </View>
                  )}
                  {missing.length > 0 && (
                    <View style={styles.statusRow}>
                      <Ionicons name="close-circle" size={16} color={theme.colors.error} style={{ marginRight: theme.spacing.xs }} />
                      <Text style={styles.statusText}>Missing: {missing.join(', ')}</Text>
                    </View>
                  )}
                </View>
              );
            })}
          </Card>
        )}

        {/* Jan Aushadhi Section */}
        {mapHtml && (
          <Card style={styles.resultsCard}>
            <View style={styles.resultsHeader}>
              <Ionicons name="medical" size={24} color={theme.colors.primary} style={{ marginRight: theme.spacing.sm }} />
              <Text style={styles.resultsTitle}>Jan Aushadhi - Government Medicine Initiative</Text>
            </View>

            {loadingJanaushadhi ? (
              <View style={styles.loadingContainer}>
                <ActivityIndicator size="large" color={theme.colors.primary} />
                <Text style={styles.loadingText}>Loading Jan Aushadhi prices...</Text>
              </View>
            ) : janaushadhiData ? (
              <>
                {/* Medicine Prices */}
                {janaushadhiData.prices && janaushadhiData.prices.length > 0 && (
                  <View style={styles.janaSection}>
                    <Text style={styles.janaSectionTitle}>Medicine Prices</Text>
                    {janaushadhiData.prices.map((item, idx) => (
                      <View key={idx} style={styles.janaPriceItem}>
                        <View style={styles.janaPriceRow}>
                          <Text style={styles.janaMedicineName}>{item.Medicine}</Text>
                          <Text style={styles.janaPrice}>{item.Price}</Text>
                        </View>
                        {item.Matched_Name && item.Matched_Name !== item.Medicine && (
                          <Text style={styles.janaMatchedName}>Matched: {item.Matched_Name}</Text>
                        )}
                        {item.Vendor && (
                          <Text style={styles.janaVendor}>Vendor: {item.Vendor}</Text>
                        )}
                      </View>
                    ))}
                  </View>
                )}

                {/* Clinic Locations */}
                {janaushadhiData.clinics && janaushadhiData.clinics.length > 0 && (
                  <View style={styles.janaSection}>
                    <Text style={styles.janaSectionTitle}>Jan Aushadhi Clinic Locations</Text>
                    {janaushadhiData.clinics.map((clinic, idx) => (
                      <View key={idx} style={styles.janaClinicItem}>
                        <View style={styles.janaClinicHeader}>
                          <Ionicons name="location" size={18} color={theme.colors.primary} style={{ marginRight: theme.spacing.xs }} />
                          <Text style={styles.janaClinicName}>{clinic.name}</Text>
                        </View>
                        <Text style={styles.janaClinicAddress}>{clinic.address}</Text>
                      </View>
                    ))}
                  </View>
                )}
              </>
            ) : (
              <Text style={styles.emptyText}>No Jan Aushadhi data available</Text>
            )}
          </Card>
        )}

        {/* Map */}
        {mapHtml && (
          <Card style={styles.mapCard}>
            <View style={styles.resultsHeader}>
              <Ionicons name="map" size={24} color={theme.colors.primary} style={{ marginRight: theme.spacing.sm }} />
              <Text style={styles.resultsTitle}>Delivery Map</Text>
            </View>
            <View style={styles.mapContainer}>
              {Platform.OS === 'web' ? (
                <iframe
                  srcDoc={mapHtml}
                  style={{ width: '100%', height: '100%', border: 'none', borderRadius: 12 }}
                  title="Delivery Map"
                  sandbox="allow-scripts allow-same-origin allow-popups allow-popups-to-escape-sandbox"
                />
              ) : WebView ? (
                <WebView
                  source={{ html: mapHtml }}
                  style={{ flex: 1 }}
                  javaScriptEnabled={true}
                  domStorageEnabled={true}
                />
              ) : (
                <Text>WebView not available</Text>
              )}
            </View>
            <View style={styles.mapLegend}>
              <View style={styles.legendItem}>
                <View style={[styles.legendDot, { backgroundColor: theme.colors.success, marginRight: theme.spacing.xs }]} />
                <Text style={styles.legendText}>All Available</Text>
              </View>
              <View style={styles.legendItem}>
                <View style={[styles.legendDot, { backgroundColor: theme.colors.warning, marginRight: theme.spacing.xs }]} />
                <Text style={styles.legendText}>Has Alternatives</Text>
              </View>
              <View style={styles.legendItem}>
                <View style={[styles.legendDot, { backgroundColor: theme.colors.error, marginRight: theme.spacing.xs }]} />
                <Text style={styles.legendText}>Some Missing</Text>
              </View>
            </View>
          </Card>
        )}

        {/* Delivery Button - Show after map */}
        {mapHtml && pharmacyResults && pharmacyResults.ranked_stores && pharmacyResults.ranked_stores.length > 0 && (
          <GradientButton
            title={deliveryAssigned ? 'Delivery Assigned ✓' : 'Request Delivery'}
            onPress={requestDelivery}
            disabled={loadingMap || !location || deliveryAssigned}
            loading={loadingMap}
            variant={deliveryAssigned ? "secondary" : "primary"}
            style={styles.deliveryButton}
          />
        )}

        {/* Delivery Agent Info */}
        {deliveryAssigned && deliveryAgent && (
          <Card style={styles.agentCard}>
            <View style={styles.agentHeader}>
              <Ionicons name="bicycle" size={24} color={theme.colors.primary} style={{ marginRight: theme.spacing.sm }} />
              <Text style={styles.agentTitle}>Delivery Agent Assigned</Text>
            </View>
            <View style={styles.agentInfo}>
              <View style={styles.agentRow}>
                <Ionicons name="person" size={18} color={theme.colors.textSecondary} style={{ marginRight: theme.spacing.xs }} />
                <Text style={styles.agentText}>{deliveryAgent.name}</Text>
              </View>
              <View style={styles.agentRow}>
                <Ionicons name="call" size={18} color={theme.colors.textSecondary} style={{ marginRight: theme.spacing.xs }} />
                <Text style={styles.agentText}>{deliveryAgent.phone}</Text>
              </View>
              <View style={styles.agentRow}>
                <Ionicons name="car" size={18} color={theme.colors.textSecondary} style={{ marginRight: theme.spacing.xs }} />
                <Text style={styles.agentText}>{deliveryAgent.vehicle}</Text>
              </View>

              {/* Delivery Distance and Price Details */}
              {deliveryAgent.assignment && (
                <>
                  <View style={styles.deliveryDivider} />
                  <Text style={styles.deliverySectionTitle}>Delivery Details</Text>

                  {deliveryAgent.assignment.dist1_m && (
                    <View style={styles.agentRow}>
                      <Ionicons name="navigate" size={18} color={theme.colors.textSecondary} style={{ marginRight: theme.spacing.xs }} />
                      <Text style={styles.agentText}>
                        Agent → Store: {(deliveryAgent.assignment.dist1_m / 1000).toFixed(3)} km
                      </Text>
                    </View>
                  )}

                  {deliveryAgent.assignment.dist2_m && (
                    <View style={styles.agentRow}>
                      <Ionicons name="location" size={18} color={theme.colors.textSecondary} style={{ marginRight: theme.spacing.xs }} />
                      <Text style={styles.agentText}>
                        Store → You: {(deliveryAgent.assignment.dist2_m / 1000).toFixed(3)} km
                      </Text>
                    </View>
                  )}

                  {deliveryAgent.assignment.total_m && (
                    <View style={styles.agentRow}>
                      <Ionicons name="map" size={18} color={theme.colors.primary} style={{ marginRight: theme.spacing.xs }} />
                      <Text style={[styles.agentText, styles.totalDistanceText]}>
                        Total Distance: {(deliveryAgent.assignment.total_m / 1000).toFixed(3)} km
                      </Text>
                    </View>
                  )}

                  {deliveryAgent.assignment.charge && (
                    <View style={styles.agentRow}>
                      <Ionicons name="cash" size={18} color={theme.colors.success} style={{ marginRight: theme.spacing.xs }} />
                      <Text style={[styles.agentText, styles.deliveryPriceText]}>
                        Delivery Charge: ₹{deliveryAgent.assignment.charge}
                      </Text>
                    </View>
                  )}
                </>
              )}
            </View>
          </Card>
        )}

        {/* Show message if delivery assigned but no agent details */}
        {deliveryAssigned && !deliveryAgent && (
          <Card style={styles.agentCard}>
            <View style={styles.agentHeader}>
              <Ionicons name="information-circle" size={24} color={theme.colors.warning} style={{ marginRight: theme.spacing.sm }} />
              <Text style={styles.agentTitle}>Delivery Assigned</Text>
            </View>
            <Text style={styles.agentText}>
              Delivery route has been added to the map. Check the map for the purple route showing the agent's path from their location to the store and then to your location.
            </Text>
          </Card>
        )}

        {/* Store Selection Modal */}
        <Modal
          visible={showStoreModal}
          transparent={true}
          animationType="slide"
          onRequestClose={() => setShowStoreModal(false)}
        >
          <View style={styles.modalOverlay}>
            <View style={styles.modalContent}>
              <View style={styles.modalHeader}>
                <Text style={styles.modalTitle}>Select Pharmacy for Delivery</Text>
                <TouchableOpacity
                  onPress={() => setShowStoreModal(false)}
                  style={styles.modalCloseButton}
                >
                  <Ionicons name="close" size={24} color={theme.colors.text} />
                </TouchableOpacity>
              </View>
              <ScrollView style={styles.modalScrollView} showsVerticalScrollIndicator={false}>
                {pharmacyResults && pharmacyResults.ranked_stores && pharmacyResults.ranked_stores.map((store, idx) => {
                  const status = store.medicine_status || {};
                  const missing = (status.missing || []).filter((med, idx, arr) => arr.indexOf(med) === idx);
                  const alternatives = (status.alternative || []).filter((alt, idx, arr) => {
                    const reqName = typeof alt === 'string' ? alt : alt.requested;
                    return arr.findIndex(a => {
                      const aReq = typeof a === 'string' ? a : a.requested;
                      return aReq === reqName;
                    }) === idx;
                  });
                  const available = (status.available || []).filter((med, idx, arr) => arr.indexOf(med) === idx);

                  const availableFiltered = available.filter(med => !missing.includes(med));
                  const alternativesFiltered = alternatives.filter(alt => {
                    const reqName = typeof alt === 'string' ? alt : alt.requested;
                    return !missing.includes(reqName);
                  });
                  const alternativesFinal = alternativesFiltered.filter(alt => {
                    const reqName = typeof alt === 'string' ? alt : alt.requested;
                    return !availableFiltered.includes(reqName);
                  });

                  const statusColor =
                    idx === 0
                      ? theme.colors.success
                      : missing.length > 0
                        ? theme.colors.error
                        : theme.colors.warning;

                  return (
                    <TouchableOpacity
                      key={idx}
                      style={styles.storeOption}
                      onPress={() => assignDeliveryToStore(store)}
                      activeOpacity={0.7}
                    >
                      <View style={styles.storeOptionHeader}>
                        <View style={[styles.storeOptionBadge, { backgroundColor: `${statusColor}20` }]}>
                          <View style={[styles.storeOptionDot, { backgroundColor: statusColor }]} />
                        </View>
                        <View style={styles.storeOptionInfo}>
                          <Text style={styles.storeOptionName}>{store.store_name}</Text>
                          <Text style={styles.storeOptionDistance}>
                            {store.distance_from_source?.toFixed(2)} km away • ₹{store.total_price?.toFixed(2) || 'N/A'}
                          </Text>
                        </View>
                        <Ionicons name="chevron-forward" size={20} color={theme.colors.textLight} />
                      </View>
                      <View style={styles.storeOptionStatus}>
                        {availableFiltered.length > 0 && (
                          <Text style={[styles.storeOptionStatusText, { color: theme.colors.success }]}>
                            ✓ {availableFiltered.length} available
                          </Text>
                        )}
                        {alternativesFinal.length > 0 && (
                          <Text style={[styles.storeOptionStatusText, { color: theme.colors.warning }]}>
                            ⚠ {alternativesFinal.length} alternatives
                          </Text>
                        )}
                        {missing.length > 0 && (
                          <Text style={[styles.storeOptionStatusText, { color: theme.colors.error }]}>
                            ✗ {missing.length} missing
                          </Text>
                        )}
                      </View>
                    </TouchableOpacity>
                  );
                })}
              </ScrollView>
            </View>
          </View>
        </Modal>
      </ScrollView>
    </SafeAreaView>
  );
};

const styles = StyleSheet.create({
  container: {
    flex: 1,
    backgroundColor: theme.colors.background,
  },
  scrollView: {
    flex: 1,
  },
  scrollContent: {
    padding: theme.spacing.md,
    paddingBottom: 100,
  },
  header: {
    marginBottom: theme.spacing.xl,
    alignItems: 'center',
  },
  title: {
    ...theme.typography.h1,
    color: theme.colors.text,
    marginBottom: theme.spacing.xs,
    textAlign: 'center',
  },
  subtitle: {
    ...theme.typography.body,
    color: theme.colors.textSecondary,
  },
  locationCard: {
    marginBottom: theme.spacing.md,
  },
  locationRow: {
    flexDirection: 'row',
    alignItems: 'center',
  },
  locationInfo: {
    marginLeft: theme.spacing.md,
    flex: 1,
  },
  locationLabel: {
    ...theme.typography.bodySmall,
    fontWeight: '600',
    color: theme.colors.textSecondary,
    marginBottom: theme.spacing.xs,
  },
  locationText: {
    ...theme.typography.body,
    color: theme.colors.text,
  },
  infoCard: {
    marginBottom: theme.spacing.md,
    alignItems: 'center',
  },
  infoText: {
    ...theme.typography.body,
    color: theme.colors.textSecondary,
    textAlign: 'center',
    marginVertical: theme.spacing.md,
  },
  infoButton: {
    width: '100%',
  },
  medicinesCard: {
    marginBottom: theme.spacing.md,
  },
  refreshButton: {
    marginLeft: 'auto',
    padding: theme.spacing.xs,
  },
  medicinesList: {
    flexDirection: 'row',
    flexWrap: 'wrap',
    marginHorizontal: -theme.spacing.xs,
    marginTop: theme.spacing.sm,
    marginBottom: theme.spacing.sm,
  },
  medicineBadge: {
    backgroundColor: `${theme.colors.primary}15`,
    paddingHorizontal: theme.spacing.md,
    paddingVertical: theme.spacing.xs,
    borderRadius: theme.borderRadius.full,
    borderWidth: 1,
    borderColor: theme.colors.primary,
  },
  medicineBadgeText: {
    ...theme.typography.bodySmall,
    color: theme.colors.primary,
    fontWeight: '600',
  },
  medicineCount: {
    ...theme.typography.caption,
    color: theme.colors.textSecondary,
    textAlign: 'center',
    marginTop: theme.spacing.xs,
    fontStyle: 'italic',
  },
  findButton: {
    marginBottom: theme.spacing.xl,
  },
  resultsCard: {
    marginBottom: theme.spacing.md,
  },
  resultsHeader: {
    flexDirection: 'row',
    alignItems: 'center',
    marginBottom: theme.spacing.md,
  },
  resultsTitle: {
    ...theme.typography.h4,
    color: theme.colors.text,
  },
  pharmacyItem: {
    paddingVertical: theme.spacing.md,
    borderBottomWidth: 1,
    borderBottomColor: theme.colors.border,
  },
  pharmacyHeader: {
    flexDirection: 'row',
    alignItems: 'center',
    marginBottom: theme.spacing.sm,
  },
  pharmacyRank: {
    width: 32,
    height: 32,
    borderRadius: 16,
    backgroundColor: theme.colors.primary,
    alignItems: 'center',
    justifyContent: 'center',
    marginRight: theme.spacing.md,
  },
  rankNumber: {
    ...theme.typography.bodySmall,
    fontWeight: '700',
    color: '#FFFFFF',
  },
  pharmacyInfo: {
    flex: 1,
  },
  pharmacyName: {
    ...theme.typography.h4,
    color: theme.colors.text,
    marginBottom: theme.spacing.xs,
  },
  pharmacyDistance: {
    ...theme.typography.bodySmall,
    color: theme.colors.textSecondary,
  },
  statusBadge: {
    width: 32,
    height: 32,
    borderRadius: 16,
    alignItems: 'center',
    justifyContent: 'center',
  },
  statusDot: {
    width: 12,
    height: 12,
    borderRadius: 6,
  },
  pharmacyPrice: {
    ...theme.typography.body,
    fontWeight: '600',
    color: theme.colors.primary,
    marginBottom: theme.spacing.xs,
  },
  statusRow: {
    flexDirection: 'row',
    alignItems: 'center',
    marginTop: theme.spacing.xs,
  },
  statusText: {
    ...theme.typography.bodySmall,
    color: theme.colors.text,
    flex: 1,
  },
  mapCard: {
    marginBottom: theme.spacing.md,
  },
  mapContainer: {
    width: '100%',
    height: 400,
    borderRadius: theme.borderRadius.md,
    overflow: 'hidden',
    marginBottom: theme.spacing.md,
  },
  mapLegend: {
    flexDirection: 'row',
    justifyContent: 'space-around',
    flexWrap: 'wrap',
  },
  legendItem: {
    flexDirection: 'row',
    alignItems: 'center',
    marginBottom: theme.spacing.xs,
  },
  legendDot: {
    width: 12,
    height: 12,
    borderRadius: 6,
  },
  legendText: {
    ...theme.typography.caption,
    color: theme.colors.textSecondary,
  },
  deliveryButton: {
    marginBottom: theme.spacing.md,
  },
  agentCard: {
    marginBottom: theme.spacing.md,
    backgroundColor: `${theme.colors.primary}10`,
  },
  agentHeader: {
    flexDirection: 'row',
    alignItems: 'center',
    marginBottom: theme.spacing.md,
  },
  agentTitle: {
    ...theme.typography.h4,
    color: theme.colors.text,
  },
  agentInfo: {
    marginTop: theme.spacing.xs,
  },
  agentRow: {
    flexDirection: 'row',
    alignItems: 'center',
    marginBottom: theme.spacing.xs,
  },
  agentText: {
    ...theme.typography.body,
    color: theme.colors.text,
  },
  deliveryDivider: {
    height: 1,
    backgroundColor: theme.colors.border,
    marginVertical: theme.spacing.md,
  },
  deliverySectionTitle: {
    ...theme.typography.h4,
    color: theme.colors.text,
    marginBottom: theme.spacing.sm,
  },
  totalDistanceText: {
    fontWeight: '600',
    color: theme.colors.primary,
    fontSize: 16,
  },
  deliveryPriceText: {
    fontWeight: '700',
    color: theme.colors.success,
    fontSize: 18,
  },
  modalOverlay: {
    flex: 1,
    backgroundColor: 'rgba(0, 0, 0, 0.5)',
    justifyContent: 'flex-end',
  },
  modalContent: {
    backgroundColor: theme.colors.surface,
    borderTopLeftRadius: theme.borderRadius.xl,
    borderTopRightRadius: theme.borderRadius.xl,
    maxHeight: '80%',
    paddingBottom: theme.spacing.xl,
  },
  modalHeader: {
    flexDirection: 'row',
    alignItems: 'center',
    justifyContent: 'space-between',
    padding: theme.spacing.lg,
    borderBottomWidth: 1,
    borderBottomColor: theme.colors.border,
  },
  modalTitle: {
    ...theme.typography.h3,
    color: theme.colors.text,
    flex: 1,
  },
  modalCloseButton: {
    padding: theme.spacing.xs,
  },
  modalScrollView: {
    flex: 1,
  },
  storeOption: {
    padding: theme.spacing.md,
    borderBottomWidth: 1,
    borderBottomColor: theme.colors.border,
  },
  storeOptionHeader: {
    flexDirection: 'row',
    alignItems: 'center',
    marginBottom: theme.spacing.sm,
  },
  storeOptionBadge: {
    width: 32,
    height: 32,
    borderRadius: 16,
    alignItems: 'center',
    justifyContent: 'center',
    marginRight: theme.spacing.md,
  },
  storeOptionDot: {
    width: 12,
    height: 12,
    borderRadius: 6,
  },
  storeOptionInfo: {
    flex: 1,
  },
  storeOptionName: {
    ...theme.typography.h4,
    color: theme.colors.text,
    marginBottom: theme.spacing.xs,
  },
  storeOptionDistance: {
    ...theme.typography.bodySmall,
    color: theme.colors.textSecondary,
  },
  storeOptionStatus: {
    flexDirection: 'row',
    flexWrap: 'wrap',
    marginTop: theme.spacing.xs,
  },
  storeOptionStatusText: {
    ...theme.typography.caption,
    fontWeight: '600',
    marginRight: theme.spacing.sm,
  },
  // Jan Aushadhi styles
  janaSection: {
    marginTop: theme.spacing.md,
  },
  janaSectionTitle: {
    ...theme.typography.h4,
    color: theme.colors.text,
    marginBottom: theme.spacing.md,
    fontWeight: '600',
  },
  janaPriceItem: {
    paddingVertical: theme.spacing.sm,
    paddingHorizontal: theme.spacing.md,
    backgroundColor: theme.colors.surface,
    borderRadius: theme.borderRadius.md,
    marginBottom: theme.spacing.sm,
  },
  janaPriceRow: {
    flexDirection: 'row',
    justifyContent: 'space-between',
    alignItems: 'center',
    marginBottom: theme.spacing.xs,
  },
  janaMedicineName: {
    ...theme.typography.body,
    fontWeight: '600',
    color: theme.colors.text,
    flex: 1,
  },
  janaPrice: {
    ...theme.typography.body,
    fontWeight: '700',
    color: theme.colors.success,
  },
  janaMatchedName: {
    ...theme.typography.bodySmall,
    color: theme.colors.textSecondary,
    marginTop: theme.spacing.xs,
  },
  janaVendor: {
    ...theme.typography.bodySmall,
    color: theme.colors.textSecondary,
    marginTop: theme.spacing.xs,
  },
  janaClinicItem: {
    paddingVertical: theme.spacing.md,
    paddingHorizontal: theme.spacing.md,
    backgroundColor: theme.colors.surface,
    borderRadius: theme.borderRadius.md,
    marginBottom: theme.spacing.sm,
  },
  janaClinicHeader: {
    flexDirection: 'row',
    alignItems: 'center',
    marginBottom: theme.spacing.xs,
  },
  janaClinicName: {
    ...theme.typography.body,
    fontWeight: '600',
    color: theme.colors.text,
    flex: 1,
  },
  janaClinicAddress: {
    ...theme.typography.bodySmall,
    color: theme.colors.textSecondary,
    marginLeft: theme.spacing.lg,
  },
  emptyText: {
    ...theme.typography.body,
    color: theme.colors.textSecondary,
    textAlign: 'center',
    paddingVertical: theme.spacing.lg,
  },
});

export default PharmaciesScreen;

