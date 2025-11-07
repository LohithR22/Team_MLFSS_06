import React, { useState } from 'react';
import {
  View,
  Text,
  StyleSheet,
  ScrollView,
  Image,
  Alert,
  ActivityIndicator,
  Platform,
  TouchableOpacity,
  Linking,
  TextInput,
} from 'react-native';
import { SafeAreaView } from 'react-native-safe-area-context';
import { StatusBar } from 'expo-status-bar';
import { Ionicons } from '@expo/vector-icons';
import * as ImagePicker from 'expo-image-picker';
import { useRouter } from 'expo-router';
// AsyncStorage for cross-screen data sharing
import AsyncStorage from '@react-native-async-storage/async-storage';
import { theme } from '../../constants/theme';
import Card from '../../components/Card';
import GradientButton from '../../components/GradientButton';

const PrescriptionScreen = () => {
  const router = useRouter();
  const [imageUri, setImageUri] = useState(null);
  const [uploading, setUploading] = useState(false);
  const [medicines, setMedicines] = useState(null);
  const [scraping, setScraping] = useState(false);
  const [scrapeResults, setScrapeResults] = useState(null);
  const [medicineInput, setMedicineInput] = useState('');

  const pickImage = async () => {
    const { status } = await ImagePicker.requestMediaLibraryPermissionsAsync();
    if (status !== 'granted') {
      Alert.alert('Permission required', 'We need access to your photos to upload a prescription.');
      return;
    }

    const result = await ImagePicker.launchImageLibraryAsync({
      mediaTypes: 'images',
      allowsEditing: true,
      aspect: [4, 3],
      quality: 1,
    });

    if (!result.canceled && result.assets && result.assets.length > 0) {
      setImageUri(result.assets[0].uri);
      setMedicines(null);
      setScrapeResults(null);
      setMedicineInput(''); // Clear manual input when image is selected
    }
  };

  const takePhoto = async () => {
    const { status } = await ImagePicker.requestCameraPermissionsAsync();
    if (status !== 'granted') {
      Alert.alert('Permission required', 'We need access to your camera to take a photo.');
      return;
    }

    const result = await ImagePicker.launchCameraAsync({
      allowsEditing: true,
      aspect: [4, 3],
      quality: 1,
    });

    if (!result.canceled && result.assets && result.assets.length > 0) {
      setImageUri(result.assets[0].uri);
      setMedicines(null);
      setScrapeResults(null);
      setMedicineInput(''); // Clear manual input when image is selected
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
        throw new Error(data?.error || 'Upload failed');
      }
      const meds = data.medicines || [];
      setMedicines(meds);
      
      // Save medicines to AsyncStorage for use in pharmacies screen
      if (meds.length > 0) {
        try {
          await AsyncStorage.setItem('extractedMedicines', JSON.stringify(meds));
          console.log('✅ Medicines saved to AsyncStorage:', meds);
          
          // On web, also try localStorage as fallback
          if (Platform.OS === 'web') {
            try {
              localStorage.setItem('extractedMedicines', JSON.stringify(meds));
              console.log('✅ Medicines also saved to localStorage (web)');
            } catch (e) {
              console.warn('Failed to save to localStorage:', e);
            }
          }
        } catch (e) {
          console.error('❌ Failed to save medicines to AsyncStorage:', e);
          // Try localStorage as fallback
          if (Platform.OS === 'web') {
            try {
              localStorage.setItem('extractedMedicines', JSON.stringify(meds));
              console.log('✅ Medicines saved to localStorage as fallback');
            } catch (localE) {
              console.error('❌ Failed to save to localStorage too:', localE);
              Alert.alert('Warning', 'Medicines extracted but failed to save for pharmacy search.');
            }
          } else {
            Alert.alert('Warning', 'Medicines extracted but failed to save for pharmacy search.');
          }
        }
      } else {
        // Clear AsyncStorage if no medicines found
        try {
          await AsyncStorage.removeItem('extractedMedicines');
          if (Platform.OS === 'web') {
            localStorage.removeItem('extractedMedicines');
          }
        } catch (e) {
          console.error('Failed to clear medicines from storage:', e);
        }
      }

      // Trigger scraping
      if (meds.length > 0) {
        try {
          setScraping(true);
          const resp = await fetch('http://localhost:3000/scrape', {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({ medicines: meds }),
          });
          const scrape = await resp.json();
          if (!resp.ok) throw new Error(scrape?.error || 'Scrape failed');
          setScrapeResults(scrape.results || []);
        } catch (err) {
          Alert.alert('Scrape Error', err?.message || 'Failed to scrape');
        } finally {
          setScraping(false);
        }
      }
      Alert.alert(
        'Success', 
        `OCR completed successfully! ${meds.length} medicine(s) extracted.`,
        [
          {
            text: 'Find Pharmacies',
            onPress: () => router.push('/(tabs)/pharmacies'),
            style: 'default',
          },
          {
            text: 'OK',
            style: 'cancel',
          },
        ]
      );
    } catch (e) {
      Alert.alert('Error', e?.message || 'Failed to upload');
    } finally {
      setUploading(false);
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
          <Text style={styles.title}>Prescription - Online Prices</Text>
          <Text style={styles.subtitle}>
            Upload or take a photo of your prescription to extract medicines and compare online prices
          </Text>
        </View>

        {/* Image Selection */}
        <Card style={styles.imageCard}>
          {imageUri ? (
            <View>
              <Image source={{ uri: imageUri }} style={styles.image} resizeMode="contain" />
              <TouchableOpacity
                style={styles.removeButton}
                onPress={() => {
                  setImageUri(null);
                  setMedicines(null);
                  setScrapeResults(null);
                  setMedicineInput(''); // Clear manual input when removing image
                }}
              >
                <Ionicons name="close-circle" size={32} color={theme.colors.error} />
              </TouchableOpacity>
            </View>
          ) : (
            <View style={styles.placeholder}>
              <Ionicons name="document-text" size={64} color={theme.colors.textLight} />
              <Text style={styles.placeholderText}>No prescription selected</Text>
            </View>
          )}
        </Card>

        {/* Action Buttons */}
        <View style={styles.actions}>
          <TouchableOpacity
            style={[styles.actionButton, styles.galleryButton]}
            onPress={pickImage}
            activeOpacity={0.8}
          >
            <Ionicons name="images" size={24} color={theme.colors.primary} style={{ marginRight: theme.spacing.xs }} />
            <Text style={styles.actionButtonText}>Choose from Gallery</Text>
          </TouchableOpacity>
          <TouchableOpacity
            style={[styles.actionButton, styles.cameraButton]}
            onPress={takePhoto}
            activeOpacity={0.8}
          >
            <Ionicons name="camera" size={24} color={theme.colors.secondary} style={{ marginRight: theme.spacing.xs }} />
            <Text style={styles.actionButtonText}>Take Photo</Text>
          </TouchableOpacity>
        </View>

        {/* Manual Medicine Input */}
        <Card style={styles.inputCard}>
          <View style={styles.inputHeader}>
            <Ionicons name="create-outline" size={20} color={theme.colors.primary} style={{ marginRight: theme.spacing.sm }} />
            <Text style={styles.inputLabel}>Or Enter Medicine Names Manually</Text>
          </View>
          <View style={styles.inputContainer}>
            <TextInput
              style={styles.medicineTextInput}
              placeholder="e.g., Ulmeal-D, Progon, Augmentin, Enzoflam..."
              placeholderTextColor={theme.colors.textLight}
              value={medicineInput}
              onChangeText={setMedicineInput}
              multiline
              numberOfLines={3}
              textAlignVertical="top"
            />
            {medicineInput.length > 0 && (
              <TouchableOpacity
                style={styles.clearButton}
                onPress={() => {
                  setMedicineInput('');
                  setMedicines(null);
                  setScrapeResults(null);
                }}
                activeOpacity={0.7}
              >
                <Ionicons name="close-circle" size={20} color={theme.colors.textLight} />
              </TouchableOpacity>
            )}
          </View>
          {medicineInput.trim().length > 0 && (
            <TouchableOpacity
              style={styles.processManualButton}
              onPress={async () => {
                // Parse comma-separated medicine names
                const medsList = medicineInput
                  .split(',')
                  .map((m) => m.trim())
                  .filter((m) => m.length > 0);
                
                if (medsList.length > 0) {
                  setMedicines(medsList);
                  setImageUri(null); // Clear image when using manual input
                  
                  // Save to AsyncStorage
                  try {
                    await AsyncStorage.setItem('extractedMedicines', JSON.stringify(medsList));
                    console.log('✅ Manual medicines saved to AsyncStorage:', medsList);
                    
                    if (Platform.OS === 'web') {
                      try {
                        localStorage.setItem('extractedMedicines', JSON.stringify(medsList));
                      } catch (e) {
                        console.warn('Failed to save to localStorage:', e);
                      }
                    }
                  } catch (e) {
                    console.error('Failed to save medicines:', e);
                  }
                  
                  // Trigger scraping
                  try {
                    setScraping(true);
                    const resp = await fetch('http://localhost:3000/scrape', {
                      method: 'POST',
                      headers: { 'Content-Type': 'application/json' },
                      body: JSON.stringify({ medicines: medsList }),
                    });
                    const scrape = await resp.json();
                    if (!resp.ok) throw new Error(scrape?.error || 'Scrape failed');
                    setScrapeResults(scrape.results || []);
                    Alert.alert('Success', `${medsList.length} medicine(s) added. Price comparison started!`);
                  } catch (err) {
                    Alert.alert('Scrape Error', err?.message || 'Failed to scrape prices');
                  } finally {
                    setScraping(false);
                  }
                } else {
                  Alert.alert('Error', 'Please enter at least one medicine name');
                }
              }}
              activeOpacity={0.8}
            >
              <Ionicons name="search" size={20} color="#FFFFFF" style={{ marginRight: theme.spacing.xs }} />
              <Text style={styles.processManualButtonText}>Search Prices</Text>
            </TouchableOpacity>
          )}
        </Card>

        <GradientButton
          title={uploading ? 'Processing...' : 'Extract Medicines'}
          onPress={uploadImage}
          disabled={!imageUri || uploading}
          loading={uploading}
          style={styles.uploadButton}
        />

        {/* Medicines List */}
        {medicines && medicines.length > 0 && (
          <Card style={styles.resultsCard}>
            <View style={styles.resultsHeader}>
              <Ionicons name="checkmark-circle" size={24} color={theme.colors.success} style={{ marginRight: theme.spacing.sm }} />
              <Text style={styles.resultsTitle}>Extracted Medicines</Text>
            </View>
            {medicines.map((medicine, idx) => (
              <View key={idx} style={styles.medicineItem}>
                <View style={styles.medicineBullet} />
                <Text style={styles.medicineText}>{medicine}</Text>
              </View>
            ))}
          </Card>
        )}

        {/* Scraping Results */}
        {scraping && (
          <Card style={styles.loadingCard}>
            <ActivityIndicator size="large" color={theme.colors.primary} />
            <Text style={styles.loadingText}>Searching for prices...</Text>
          </Card>
        )}

        {scrapeResults && scrapeResults.length > 0 && (
          <Card style={styles.resultsCard}>
            <View style={styles.resultsHeader}>
              <Ionicons name="pricetag" size={24} color={theme.colors.accent} style={{ marginRight: theme.spacing.sm }} />
              <Text style={styles.resultsTitle}>Price Comparison</Text>
            </View>
            {scrapeResults.map((result, idx) => (
              <View key={idx} style={styles.medicineComparisonCard}>
                {/* Medicine Name */}
                <View style={styles.medicineNameHeader}>
                  <Ionicons name="medical" size={20} color={theme.colors.primary} style={{ marginRight: theme.spacing.sm }} />
                  <Text style={styles.medicineName}>{result.medicine}</Text>
                </View>

                {/* Two Column Layout: Apollo (Left) and Netmed (Right) */}
                <View style={styles.columnsContainer}>
                  {/* Left Column - Apollo */}
                  <View style={styles.column}>
                    {result.apollo ? (
                      <View style={styles.pharmacySection}>
                        <View style={styles.pharmacyHeader}>
                          <View style={[styles.pharmacyBadge, { backgroundColor: `${theme.colors.primary}20` }]}>
                            <Text style={[styles.pharmacyName, { color: theme.colors.primary }]}>Apollo</Text>
                          </View>
                        </View>

                        {/* Best Choice */}
                        {result.apollo.best_choice && (
                          <View style={styles.productCard}>
                            <View style={styles.bestChoiceBadge}>
                              <Ionicons name="star" size={14} color={theme.colors.accent} />
                              <Text style={styles.bestChoiceText}>Best Choice</Text>
                            </View>
                            <Text style={styles.productName} numberOfLines={3}>{result.apollo.best_choice.name || 'N/A'}</Text>
                            <Text style={styles.productPrice}>₹{result.apollo.best_choice.price || 'N/A'}</Text>
                            {result.apollo.best_choice.link && result.apollo.best_choice.link !== 'N/A' && (
                              <TouchableOpacity
                                style={styles.linkButton}
                                onPress={() => Linking.openURL(result.apollo.best_choice.link)}
                                activeOpacity={0.7}
                              >
                                <Ionicons name="open-outline" size={16} color={theme.colors.primary} style={{ marginRight: 6 }} />
                                <Text style={styles.linkText}>View Product</Text>
                              </TouchableOpacity>
                            )}
                          </View>
                        )}

                        {/* Alternatives (limit to 2) */}
                        {result.apollo.alternatives && result.apollo.alternatives.slice(0, 2).map((alt, altIdx) => (
                          <View key={altIdx} style={[styles.productCard, styles.alternativeCard]}>
                            <View style={styles.alternativeBadge}>
                              <Text style={styles.alternativeText}>Alt {altIdx + 1}</Text>
                            </View>
                            <Text style={styles.productName} numberOfLines={3}>{alt.name || 'N/A'}</Text>
                            <Text style={styles.productPrice}>₹{alt.price || 'N/A'}</Text>
                            {alt.link && alt.link !== 'N/A' && (
                              <TouchableOpacity
                                style={styles.linkButton}
                                onPress={() => Linking.openURL(alt.link)}
                                activeOpacity={0.7}
                              >
                                <Ionicons name="open-outline" size={16} color={theme.colors.primary} style={{ marginRight: 6 }} />
                                <Text style={styles.linkText}>View Product</Text>
                              </TouchableOpacity>
                            )}
                          </View>
                        ))}

                        {/* No Apollo Results */}
                        {!result.apollo.best_choice && (!result.apollo.alternatives || result.apollo.alternatives.length === 0) && (
                          <View style={styles.noResultsCard}>
                            <Ionicons name="alert-circle" size={14} color={theme.colors.textLight} style={{ marginRight: theme.spacing.xs }} />
                            <Text style={styles.noResultsTextSmall}>No products</Text>
                          </View>
                        )}
                      </View>
                    ) : (
                      <View style={styles.pharmacySection}>
                        <View style={styles.pharmacyHeader}>
                          <View style={[styles.pharmacyBadge, { backgroundColor: `${theme.colors.primary}20` }]}>
                            <Text style={[styles.pharmacyName, { color: theme.colors.primary }]}>Apollo</Text>
                          </View>
                        </View>
                        <View style={styles.noResultsCard}>
                          <Ionicons name="alert-circle" size={14} color={theme.colors.textLight} style={{ marginRight: theme.spacing.xs }} />
                          <Text style={styles.noResultsTextSmall}>No data</Text>
                        </View>
                      </View>
                    )}
                  </View>

                  {/* Right Column - Netmed */}
                  <View style={styles.column}>
                    {result.netmed ? (
                      <View style={styles.pharmacySection}>
                        <View style={styles.pharmacyHeader}>
                          <View style={[styles.pharmacyBadge, { backgroundColor: `${theme.colors.secondary}20` }]}>
                            <Text style={[styles.pharmacyName, { color: theme.colors.secondary }]}>Netmed</Text>
                          </View>
                        </View>

                        {/* Best Choice */}
                        {result.netmed.best_choice && (
                          <View style={styles.productCard}>
                            <View style={styles.bestChoiceBadge}>
                              <Ionicons name="star" size={14} color={theme.colors.accent} />
                              <Text style={styles.bestChoiceText}>Best Choice</Text>
                            </View>
                            <Text style={styles.productName} numberOfLines={3}>{result.netmed.best_choice.name || 'N/A'}</Text>
                            <Text style={styles.productPrice}>₹{result.netmed.best_choice.price || 'N/A'}</Text>
                            {result.netmed.best_choice.link && result.netmed.best_choice.link !== 'N/A' && (
                              <TouchableOpacity
                                style={styles.linkButton}
                                onPress={() => Linking.openURL(result.netmed.best_choice.link)}
                                activeOpacity={0.7}
                              >
                                <Ionicons name="open-outline" size={16} color={theme.colors.secondary} style={{ marginRight: 6 }} />
                                <Text style={[styles.linkText, { color: theme.colors.secondary }]}>View Product</Text>
                              </TouchableOpacity>
                            )}
                          </View>
                        )}

                        {/* Alternatives (limit to 2) */}
                        {result.netmed.alternatives && result.netmed.alternatives.slice(0, 2).map((alt, altIdx) => (
                          <View key={altIdx} style={[styles.productCard, styles.alternativeCard]}>
                            <View style={styles.alternativeBadge}>
                              <Text style={styles.alternativeText}>Alt {altIdx + 1}</Text>
                            </View>
                            <Text style={styles.productName} numberOfLines={3}>{alt.name || 'N/A'}</Text>
                            <Text style={styles.productPrice}>₹{alt.price || 'N/A'}</Text>
                            {alt.link && alt.link !== 'N/A' && (
                              <TouchableOpacity
                                style={styles.linkButton}
                                onPress={() => Linking.openURL(alt.link)}
                                activeOpacity={0.7}
                              >
                                <Ionicons name="open-outline" size={16} color={theme.colors.secondary} style={{ marginRight: 6 }} />
                                <Text style={[styles.linkText, { color: theme.colors.secondary }]}>View Product</Text>
                              </TouchableOpacity>
                            )}
                          </View>
                        ))}

                        {/* No Netmed Results */}
                        {!result.netmed.best_choice && (!result.netmed.alternatives || result.netmed.alternatives.length === 0) && (
                          <View style={styles.noResultsCard}>
                            <Ionicons name="alert-circle" size={14} color={theme.colors.textLight} style={{ marginRight: theme.spacing.xs }} />
                            <Text style={styles.noResultsTextSmall}>No products</Text>
                          </View>
                        )}
                      </View>
                    ) : (
                      <View style={styles.pharmacySection}>
                        <View style={styles.pharmacyHeader}>
                          <View style={[styles.pharmacyBadge, { backgroundColor: `${theme.colors.secondary}20` }]}>
                            <Text style={[styles.pharmacyName, { color: theme.colors.secondary }]}>Netmed</Text>
                          </View>
                        </View>
                        <View style={styles.noResultsCard}>
                          <Ionicons name="alert-circle" size={14} color={theme.colors.textLight} style={{ marginRight: theme.spacing.xs }} />
                          <Text style={styles.noResultsTextSmall}>No data</Text>
                        </View>
                      </View>
                    )}
                  </View>
                </View>
              </View>
            ))}
          </Card>
        )}
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
  imageCard: {
    marginBottom: theme.spacing.md,
    padding: 0,
    overflow: 'hidden',
  },
  image: {
    width: '100%',
    height: 300,
    backgroundColor: theme.colors.background,
  },
  placeholder: {
    width: '100%',
    height: 300,
    justifyContent: 'center',
    alignItems: 'center',
    backgroundColor: theme.colors.background,
  },
  placeholderText: {
    ...theme.typography.body,
    color: theme.colors.textLight,
    marginTop: theme.spacing.md,
  },
  removeButton: {
    position: 'absolute',
    top: theme.spacing.sm,
    right: theme.spacing.sm,
    backgroundColor: theme.colors.surface,
    borderRadius: theme.borderRadius.full,
  },
  actions: {
    flexDirection: 'row',
    justifyContent: 'space-between',
    marginBottom: theme.spacing.md,
  },
  actionButton: {
    flex: 1,
    flexDirection: 'row',
    alignItems: 'center',
    justifyContent: 'center',
    padding: theme.spacing.md,
    borderRadius: theme.borderRadius.md,
    borderWidth: 2,
    marginHorizontal: theme.spacing.xs,
  },
  galleryButton: {
    borderColor: theme.colors.primary,
    backgroundColor: `${theme.colors.primary}10`,
  },
  cameraButton: {
    borderColor: theme.colors.secondary,
    backgroundColor: `${theme.colors.secondary}10`,
  },
  actionButtonText: {
    ...theme.typography.bodySmall,
    fontWeight: '600',
    color: theme.colors.text,
  },
  uploadButton: {
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
  medicineItem: {
    flexDirection: 'row',
    alignItems: 'center',
    paddingVertical: theme.spacing.sm,
    borderBottomWidth: 1,
    borderBottomColor: theme.colors.border,
  },
  medicineBullet: {
    width: 8,
    height: 8,
    borderRadius: 4,
    backgroundColor: theme.colors.primary,
    marginRight: theme.spacing.md,
  },
  medicineText: {
    ...theme.typography.body,
    color: theme.colors.text,
    flex: 1,
  },
  loadingCard: {
    alignItems: 'center',
    padding: theme.spacing.xl,
    marginBottom: theme.spacing.md,
  },
  loadingText: {
    ...theme.typography.body,
    color: theme.colors.textSecondary,
    marginTop: theme.spacing.md,
  },
  medicineComparisonCard: {
    paddingVertical: theme.spacing.lg,
    borderBottomWidth: 2,
    borderBottomColor: theme.colors.border,
    marginBottom: theme.spacing.md,
  },
  columnsContainer: {
    flexDirection: 'row',
    justifyContent: 'space-between',
    alignItems: 'flex-start',
    marginHorizontal: -theme.spacing.xs,
  },
  column: {
    flex: 1,
    marginHorizontal: theme.spacing.xs,
    minWidth: 0, // Prevents flex overflow
  },
  medicineNameHeader: {
    flexDirection: 'row',
    alignItems: 'center',
    marginBottom: theme.spacing.md,
  },
  medicineName: {
    ...theme.typography.h3,
    color: theme.colors.text,
    fontWeight: '700',
  },
  pharmacySection: {
    marginBottom: 0,
  },
  pharmacyHeader: {
    marginBottom: theme.spacing.md,
  },
  pharmacyBadge: {
    paddingHorizontal: theme.spacing.md,
    paddingVertical: theme.spacing.xs,
    borderRadius: theme.borderRadius.full,
    alignSelf: 'flex-start',
  },
  pharmacyName: {
    ...theme.typography.bodySmall,
    fontWeight: '700',
    textTransform: 'uppercase',
  },
  productCard: {
    backgroundColor: theme.colors.background,
    borderRadius: theme.borderRadius.md,
    padding: theme.spacing.sm,
    marginBottom: theme.spacing.sm,
    borderWidth: 2,
    borderColor: theme.colors.border,
    minHeight: 140,
    width: '100%',
  },
  alternativeCard: {
    borderColor: theme.colors.border,
    borderWidth: 1,
    backgroundColor: `${theme.colors.background}F0`,
  },
  bestChoiceBadge: {
    flexDirection: 'row',
    alignItems: 'center',
    backgroundColor: `${theme.colors.accent}20`,
    paddingHorizontal: theme.spacing.sm,
    paddingVertical: 4,
    borderRadius: theme.borderRadius.sm,
    alignSelf: 'flex-start',
    marginBottom: theme.spacing.sm,
  },
  bestChoiceText: {
    ...theme.typography.caption,
    fontWeight: '700',
    color: theme.colors.accent,
    marginLeft: 4,
  },
  alternativeBadge: {
    backgroundColor: `${theme.colors.textSecondary}15`,
    paddingHorizontal: theme.spacing.sm,
    paddingVertical: 4,
    borderRadius: theme.borderRadius.sm,
    alignSelf: 'flex-start',
    marginBottom: theme.spacing.sm,
  },
  alternativeText: {
    ...theme.typography.caption,
    fontWeight: '600',
    color: theme.colors.textSecondary,
  },
  productName: {
    ...theme.typography.bodySmall,
    color: theme.colors.text,
    fontWeight: '600',
    marginBottom: theme.spacing.xs,
    lineHeight: 18,
    fontSize: 13,
  },
  productPrice: {
    ...theme.typography.body,
    fontSize: 16,
    color: theme.colors.primary,
    fontWeight: '700',
    marginBottom: theme.spacing.xs,
  },
  linkButton: {
    flexDirection: 'row',
    alignItems: 'center',
    marginTop: theme.spacing.xs,
    paddingVertical: theme.spacing.xs,
  },
  linkText: {
    ...theme.typography.bodySmall,
    color: theme.colors.primary,
    fontWeight: '600',
    textDecorationLine: 'underline',
  },
  noResultsCard: {
    flexDirection: 'row',
    alignItems: 'center',
    justifyContent: 'center',
    padding: theme.spacing.sm,
    backgroundColor: `${theme.colors.textLight}10`,
    borderRadius: theme.borderRadius.md,
    marginTop: theme.spacing.sm,
    minHeight: 60,
  },
  noResultsText: {
    ...theme.typography.bodySmall,
    color: theme.colors.textSecondary,
    fontStyle: 'italic',
  },
  noResultsTextSmall: {
    ...theme.typography.caption,
    color: theme.colors.textSecondary,
    fontStyle: 'italic',
    marginLeft: theme.spacing.xs,
    fontSize: 11,
  },
  inputCard: {
    marginBottom: theme.spacing.md,
  },
  inputHeader: {
    flexDirection: 'row',
    alignItems: 'center',
    marginBottom: theme.spacing.md,
  },
  inputLabel: {
    ...theme.typography.bodySmall,
    fontWeight: '600',
    color: theme.colors.text,
  },
  inputContainer: {
    position: 'relative',
  },
  medicineTextInput: {
    ...theme.typography.body,
    backgroundColor: theme.colors.surface,
    borderWidth: 1,
    borderColor: theme.colors.border,
    borderRadius: theme.borderRadius.md,
    padding: theme.spacing.md,
    paddingRight: 40,
    color: theme.colors.text,
    minHeight: 100,
    textAlignVertical: 'top',
  },
  clearButton: {
    position: 'absolute',
    top: theme.spacing.md,
    right: theme.spacing.md,
    padding: 4,
  },
  processManualButton: {
    flexDirection: 'row',
    alignItems: 'center',
    justifyContent: 'center',
    backgroundColor: theme.colors.primary,
    paddingVertical: theme.spacing.md,
    paddingHorizontal: theme.spacing.lg,
    borderRadius: theme.borderRadius.md,
    marginTop: theme.spacing.md,
    ...theme.shadows.md,
  },
  processManualButtonText: {
    ...theme.typography.body,
    fontWeight: '600',
    color: '#FFFFFF',
  },
});

export default PrescriptionScreen;

