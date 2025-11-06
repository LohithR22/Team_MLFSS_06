import React, { useState } from 'react';
import { View, Text, Button, Image, Alert, ActivityIndicator, StyleSheet, ScrollView, Platform } from 'react-native';
import * as ImagePicker from 'expo-image-picker';
import { useRouter } from 'expo-router';

const UploadScreen: React.FC = () => {
  const [imageUri, setImageUri] = useState<string | null>(null);
  const [uploading, setUploading] = useState<boolean>(false);
  const [medicines, setMedicines] = useState<string[] | null>(null);
  const [scraping, setScraping] = useState<boolean>(false);
  const [scrapeResults, setScrapeResults] = useState<any[] | null>(null);
  const router = useRouter();

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
      const fileName = uri.split('/').pop() || `prescription.jpg`;
      const match = /\.(\w+)$/.exec(fileName);
      const type = match ? `image/${match[1]}` : `image/jpeg`;

      const formData = new FormData();
      if (Platform.OS === 'web') {
        const res = await fetch(uri);
        const blob = await res.blob();
        formData.append('image', blob, fileName);
      } else {
        formData.append('image', {
          // @ts-ignore - React Native FormData file
          uri,
          name: fileName,
          type,
        });
      }

      const response = await fetch(`http://localhost:3000/ocr/upload?cb=${Date.now()}`, {
        method: 'POST',
        body: formData,
      });

      const data = await response.json();
      if (!response.ok) {
        const detail = (data as any)?.details || (data as any)?.stderr || (data as any)?.stdout;
        throw new Error(((data as any)?.error ? `${(data as any).error}${detail ? `: ${detail}` : ''}` : null) || 'Upload failed');
      }
      const meds = data.medicines || [];
      setMedicines(meds);
      if (meds.length) {
        try {
          setScraping(true);
          const resp = await fetch(`http://localhost:3000/scrape`, {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({ medicines: meds })
          });
          const scrape = await resp.json();
          if (!resp.ok) throw new Error(scrape?.error || 'Scrape failed');
          setScrapeResults(scrape.results || []);
        } catch (e: any) {
          Alert.alert('Scrape Error', e?.message || 'Failed to scrape');
        } finally {
          setScraping(false);
        }
      } else {
        setScrapeResults([]);
      }
      Alert.alert('Success', 'OCR completed.');
    } catch (e: any) {
      Alert.alert('Error', e?.message || 'Failed to upload');
    } finally {
      setUploading(false);
    }
  };

  return (
    <ScrollView contentContainerStyle={styles.container}>
      <Text style={styles.title}>Upload Prescription</Text>
      {imageUri ? (
        <Image source={{ uri: imageUri }} style={styles.preview} resizeMode="cover" />
      ) : (
        <View style={styles.placeholder}><Text>No image selected</Text></View>
      )}
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
      <View style={{ height: 24 }} />
      <Button title="Back to Home" onPress={() => router.replace('/home')} />
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
    fontSize: 22,
    fontWeight: '600',
    marginBottom: 16,
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
    marginTop: 16,
    width: 200,
  },
  subtitle: {
    fontSize: 18,
    fontWeight: '600',
    marginBottom: 8,
  },
});

export default UploadScreen;


