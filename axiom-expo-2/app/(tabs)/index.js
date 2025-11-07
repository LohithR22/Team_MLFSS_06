import React, { useState, useEffect } from 'react';
import {
  View,
  Text,
  StyleSheet,
  ScrollView,
  TouchableOpacity,
  StatusBar,
  Platform,
} from 'react-native';
import { useRouter } from 'expo-router';
import { Ionicons } from '@expo/vector-icons';
import { SafeAreaView } from 'react-native-safe-area-context';
import * as Location from 'expo-location';
import AsyncStorage from '@react-native-async-storage/async-storage';
import { theme } from '../../constants/theme';
import Card from '../../components/Card';

const Dashboard = () => {
  const router = useRouter();
  const [location, setLocation] = useState(null);
  const [locationError, setLocationError] = useState(null);
  const [userName, setUserName] = useState(null);

  useEffect(() => {
    // Load user name from AsyncStorage
    const loadUserName = async () => {
      try {
        const storedUser = await AsyncStorage.getItem('currentUser');
        if (storedUser) {
          const userData = JSON.parse(storedUser);
          setUserName(userData.name || null);
        }
      } catch (e) {
        console.warn('Could not load user name:', e);
      }
    };

    loadUserName();

    // Get location
    (async () => {
      try {
        let { status } = await Location.requestForegroundPermissionsAsync();
        if (status !== 'granted') {
          setLocationError('Location permission denied');
          return;
        }
        let location = await Location.getCurrentPositionAsync({});
        setLocation(location.coords);
      } catch (err) {
        setLocationError('Failed to get location');
      }
    })();
  }, []);

  const features = [
    {
      id: 'prescription',
      title: 'Prescription - Online Prices',
      description: 'Upload your prescription and compare online prices from Apollo & Netmed',
      icon: 'document-text',
      color: theme.colors.primary,
      route: '/prescription',
    },
    {
      id: 'pharmacies',
      title: 'Offline Pharmacies',
      description: 'Discover nearby pharmacies with your required medicines',
      icon: 'location',
      color: theme.colors.secondary,
      route: '/pharmacies',
    },
    {
      id: 'hwc',
      title: 'HWC Report',
      description: 'View Health & Wellness Centres data across India',
      icon: 'medical',
      color: theme.colors.info,
      route: '/hwc-report',
    },
  ];

  return (
    <SafeAreaView style={styles.container} edges={['top']}>
      <StatusBar barStyle="dark-content" backgroundColor={theme.colors.background} />
      <ScrollView
        style={styles.scrollView}
        contentContainerStyle={styles.scrollContent}
        showsVerticalScrollIndicator={false}
      >
        {/* Header */}
        <View style={styles.header}>
          <View style={styles.headerContent}>
            <Text style={styles.greeting}>
              {userName ? `Welcome Back, ${userName}! 👋` : 'Welcome Back! 👋'}
            </Text>
            <Text style={styles.subtitle}>Manage your healthcare needs</Text>
          </View>
          <View style={styles.locationBadge}>
            <Ionicons name="location" size={16} color={theme.colors.primary} />
            <Text style={styles.locationText} numberOfLines={1}>
              {location
                ? `Location: ${location.latitude.toFixed(4)}, ${location.longitude.toFixed(4)}`
                : locationError ? `Location: ${locationError}` : 'Location: Getting location...'}
            </Text>
          </View>
        </View>

        {/* Features Grid */}
        <View style={styles.featuresSection}>
          <Text style={styles.sectionTitle}>Quick Actions</Text>
          {features.map((feature) => (
            <TouchableOpacity
              key={feature.id}
              onPress={() => router.push(`(tabs)${feature.route}`)}
              activeOpacity={0.7}
            >
              <Card style={styles.featureCard}>
                <View style={[styles.iconContainer, { backgroundColor: `${feature.color}15` }]}>
                  <Ionicons name={feature.icon} size={32} color={feature.color} />
                </View>
                <View style={styles.featureContent}>
                  <Text style={styles.featureTitle}>{feature.title}</Text>
                  <Text style={styles.featureDescription}>{feature.description}</Text>
                </View>
                <Ionicons
                  name="chevron-forward"
                  size={24}
                  color={theme.colors.textLight}
                />
              </Card>
            </TouchableOpacity>
          ))}
        </View>

        {/* Stats Section */}
        <View style={styles.statsSection}>
          <Text style={styles.sectionTitle}>Health Insights</Text>
          <View style={styles.statsGrid}>
            <Card style={styles.statCard}>
              <Ionicons name="heart" size={24} color={theme.colors.error} />
              <Text style={styles.statNumber}>1,50,000+</Text>
              <Text style={styles.statLabel}>HWCs Operational</Text>
            </Card>
            <Card style={styles.statCard}>
              <Ionicons name="pills" size={24} color={theme.colors.primary} />
              <Text style={styles.statNumber}>171</Text>
              <Text style={styles.statLabel}>Free Medicines</Text>
            </Card>
            <Card style={styles.statCard}>
              <Ionicons name="flask" size={24} color={theme.colors.secondary} />
              <Text style={styles.statNumber}>63</Text>
              <Text style={styles.statLabel}>Diagnostic Tests</Text>
            </Card>
          </View>
        </View>
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
  headerContent: {
    alignItems: 'center',
    width: '100%',
  },
  greeting: {
    ...theme.typography.h1,
    color: theme.colors.text,
    marginBottom: theme.spacing.xs,
    textAlign: 'center',
  },
  subtitle: {
    ...theme.typography.body,
    color: theme.colors.textSecondary,
    textAlign: 'center',
  },
  locationBadge: {
    flexDirection: 'row',
    alignItems: 'center',
    marginTop: theme.spacing.md,
    paddingHorizontal: theme.spacing.md,
    paddingVertical: theme.spacing.sm,
    backgroundColor: theme.colors.surface,
    borderRadius: theme.borderRadius.full,
    alignSelf: 'flex-start',
    ...theme.shadows.sm,
  },
  locationText: {
    ...theme.typography.caption,
    color: theme.colors.text,
    marginLeft: theme.spacing.xs,
  },
  featuresSection: {
    marginBottom: theme.spacing.xl,
  },
  sectionTitle: {
    ...theme.typography.h3,
    color: theme.colors.text,
    marginBottom: theme.spacing.md,
  },
  featureCard: {
    flexDirection: 'row',
    alignItems: 'center',
    marginBottom: theme.spacing.md,
    padding: theme.spacing.md,
  },
  iconContainer: {
    width: 64,
    height: 64,
    borderRadius: theme.borderRadius.md,
    alignItems: 'center',
    justifyContent: 'center',
    marginRight: theme.spacing.md,
  },
  featureContent: {
    flex: 1,
  },
  featureTitle: {
    ...theme.typography.h4,
    color: theme.colors.text,
    marginBottom: theme.spacing.xs,
  },
  featureDescription: {
    ...theme.typography.bodySmall,
    color: theme.colors.textSecondary,
  },
  statsSection: {
    marginBottom: theme.spacing.xl,
  },
  statsGrid: {
    flexDirection: 'row',
    flexWrap: 'wrap',
    justifyContent: 'space-between',
  },
  statCard: {
    width: '31%',
    alignItems: 'center',
    padding: theme.spacing.md,
    marginBottom: theme.spacing.sm,
  },
  statNumber: {
    ...theme.typography.h2,
    color: theme.colors.text,
    marginTop: theme.spacing.xs,
    marginBottom: theme.spacing.xs,
  },
  statLabel: {
    ...theme.typography.caption,
    color: theme.colors.textSecondary,
    textAlign: 'center',
  },
});

export default Dashboard;

