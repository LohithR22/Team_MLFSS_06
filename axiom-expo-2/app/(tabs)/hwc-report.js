import React, { useState, useEffect } from 'react';
import {
  View,
  Text,
  StyleSheet,
  ScrollView,
  TouchableOpacity,
  ActivityIndicator,
  Linking,
} from 'react-native';
import { SafeAreaView } from 'react-native-safe-area-context';
import { StatusBar } from 'expo-status-bar';
import { Ionicons } from '@expo/vector-icons';
import { theme } from '../../constants/theme';
import Card from '../../components/Card';

const HWCReportScreen = () => {
  const [hwcReport, setHwcReport] = useState(null);
  const [loadingHwc, setLoadingHwc] = useState(false);

  useEffect(() => {
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
          <Text style={styles.title}>Health & Wellness Centres</Text>
          <Text style={styles.subtitle}>Comprehensive healthcare data across India</Text>
        </View>

        {loadingHwc ? (
          <View style={styles.loadingContainer}>
            <ActivityIndicator size="large" color={theme.colors.primary} />
            <Text style={styles.loadingText}>Loading report...</Text>
          </View>
        ) : hwcReport ? (
          <>
            {/* Service Packages - First Two Cards Side by Side */}
            {hwcReport.service_packages && (
              <Card style={styles.sectionCard}>
                <Text style={styles.sectionTitle}>
                  {hwcReport.service_packages.title}
                </Text>
                <Text style={styles.sectionDescription}>
                  {hwcReport.service_packages.description}
                </Text>

                {/* First Two Cards Side by Side */}
                <View style={styles.cardsRow}>
                  {hwcReport.service_packages.cards &&
                    hwcReport.service_packages.cards.slice(0, 2).map((card, idx) => (
                      <View key={card.id || idx} style={styles.serviceCard}>
                        <Text style={styles.cardIcon}>{card.icon || '📋'}</Text>
                        <Text style={styles.cardTitle}>{card.title}</Text>
                        {card.details && (
                          <View style={styles.detailsContainer}>
                            {card.details.map((detail, dIdx) => (
                              <View key={dIdx} style={styles.detailItem}>
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

                {/* Third Card Full Width */}
                {hwcReport.service_packages.cards &&
                  hwcReport.service_packages.cards.length > 2 && (
                    <View style={styles.serviceCardFull}>
                      <Text style={styles.cardIcon}>
                        {hwcReport.service_packages.cards[2].icon || '📋'}
                      </Text>
                      <Text style={styles.cardTitle}>
                        {hwcReport.service_packages.cards[2].title}
                      </Text>
                      {hwcReport.service_packages.cards[2].services && (
                        <View style={styles.servicesList}>
                          {hwcReport.service_packages.cards[2].services.map(
                            (service, sIdx) => (
                              <View key={service.id || sIdx} style={styles.serviceItem}>
                                <Ionicons
                                  name="checkmark-circle"
                                  size={16}
                                  color={theme.colors.success}
                                  style={{ marginRight: theme.spacing.sm, marginTop: 2 }}
                                />
                                <Text style={styles.serviceText}>{service.name}</Text>
                              </View>
                            )
                          )}
                        </View>
                      )}
                    </View>
                  )}
              </Card>
            )}

            {/* State Wise Data - Scrollable */}
            {hwcReport.state_wise_data && (
              <Card style={styles.sectionCard}>
                <View style={styles.sectionHeader}>
                  <Ionicons name="map" size={24} color={theme.colors.primary} style={{ marginRight: theme.spacing.sm }} />
                  <Text style={styles.sectionTitle}>State-wise Operational HWC Data</Text>
                </View>
                <ScrollView
                  style={styles.stateScrollView}
                  nestedScrollEnabled={true}
                  showsVerticalScrollIndicator={true}
                >
                  {hwcReport.state_wise_data.map((state, idx) => (
                    <View key={idx} style={styles.stateRow}>
                      <View style={styles.stateInfo}>
                        <Text style={styles.stateName}>{state.state}</Text>
                      </View>
                      <View style={styles.stateCountBadge}>
                        <Text style={styles.stateCount}>
                          {state.operational_hwcs.toLocaleString()}
                        </Text>
                        <Text style={styles.stateLabel}>HWCs</Text>
                      </View>
                    </View>
                  ))}
                </ScrollView>
              </Card>
            )}

            {/* Official Links */}
            {hwcReport.official_links && (
              <Card style={styles.sectionCard}>
                <View style={styles.sectionHeader}>
                  <Ionicons name="link" size={24} color={theme.colors.primary} style={{ marginRight: theme.spacing.sm }} />
                  <Text style={styles.sectionTitle}>Official Links</Text>
                </View>
                {hwcReport.official_links.map((link, idx) => (
                  <TouchableOpacity
                    key={idx}
                    style={styles.linkCard}
                    onPress={() => Linking.openURL(link.url)}
                    activeOpacity={0.7}
                  >
                    <View style={styles.linkContent}>
                      <Ionicons
                        name="open-outline"
                        size={24}
                        color={theme.colors.primary}
                        style={{ marginRight: theme.spacing.md }}
                      />
                      <View style={styles.linkInfo}>
                        <Text style={styles.linkTitle}>{link.title}</Text>
                        <Text style={styles.linkDescription}>{link.description}</Text>
                        <Text style={styles.linkUrl}>{link.url}</Text>
                      </View>
                    </View>
                    <Ionicons
                      name="chevron-forward"
                      size={24}
                      color={theme.colors.textLight}
                    />
                  </TouchableOpacity>
                ))}
              </Card>
            )}
          </>
        ) : (
          <Card style={styles.errorCard}>
            <Ionicons name="alert-circle" size={48} color={theme.colors.error} />
            <Text style={styles.errorText}>No HWC report data available</Text>
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
    textAlign: 'center',
  },
  loadingContainer: {
    alignItems: 'center',
    justifyContent: 'center',
    padding: theme.spacing.xxl,
  },
  loadingText: {
    ...theme.typography.body,
    color: theme.colors.textSecondary,
    marginTop: theme.spacing.md,
  },
  sectionCard: {
    marginBottom: theme.spacing.xl,
  },
  sectionHeader: {
    flexDirection: 'row',
    alignItems: 'center',
    marginBottom: theme.spacing.md,
  },
  sectionTitle: {
    ...theme.typography.h3,
    color: theme.colors.text,
    marginBottom: theme.spacing.sm,
  },
  sectionDescription: {
    ...theme.typography.body,
    color: theme.colors.textSecondary,
    marginBottom: theme.spacing.md,
    lineHeight: 24,
  },
  cardsRow: {
    flexDirection: 'row',
    justifyContent: 'space-between',
    marginBottom: theme.spacing.md,
    marginHorizontal: -theme.spacing.xs,
  },
  serviceCard: {
    flex: 1,
    backgroundColor: theme.colors.background,
    borderRadius: theme.borderRadius.md,
    padding: theme.spacing.md,
    borderWidth: 1,
    borderColor: theme.colors.border,
    minHeight: 180,
    marginHorizontal: theme.spacing.xs,
  },
  serviceCardFull: {
    backgroundColor: theme.colors.background,
    borderRadius: theme.borderRadius.md,
    padding: theme.spacing.md,
    borderWidth: 1,
    borderColor: theme.colors.border,
    marginTop: theme.spacing.md,
  },
  cardIcon: {
    fontSize: 32,
    marginBottom: theme.spacing.sm,
  },
  cardTitle: {
    ...theme.typography.h4,
    color: theme.colors.text,
    marginBottom: theme.spacing.sm,
  },
  cardDescription: {
    ...theme.typography.bodySmall,
    color: theme.colors.textSecondary,
    marginTop: theme.spacing.sm,
    lineHeight: 20,
  },
  detailsContainer: {
    marginTop: theme.spacing.sm,
  },
  detailItem: {
    marginBottom: theme.spacing.xs,
  },
  detailLevel: {
    ...theme.typography.bodySmall,
    fontWeight: '600',
    color: theme.colors.text,
  },
  detailCount: {
    ...theme.typography.caption,
    color: theme.colors.textSecondary,
    marginTop: 2,
  },
  servicesList: {
    marginTop: theme.spacing.md,
  },
  serviceItem: {
    flexDirection: 'row',
    alignItems: 'flex-start',
    marginBottom: theme.spacing.sm,
  },
  serviceText: {
    ...theme.typography.bodySmall,
    color: theme.colors.text,
    flex: 1,
    lineHeight: 20,
  },
  stateScrollView: {
    maxHeight: 400,
    backgroundColor: theme.colors.background,
    borderRadius: theme.borderRadius.md,
    borderWidth: 1,
    borderColor: theme.colors.border,
  },
  stateRow: {
    flexDirection: 'row',
    justifyContent: 'space-between',
    alignItems: 'center',
    paddingVertical: theme.spacing.md,
    paddingHorizontal: theme.spacing.md,
    borderBottomWidth: 1,
    borderBottomColor: theme.colors.border,
  },
  stateInfo: {
    flex: 1,
  },
  stateName: {
    ...theme.typography.body,
    fontWeight: '500',
    color: theme.colors.text,
  },
  stateCountBadge: {
    alignItems: 'flex-end',
  },
  stateCount: {
    ...theme.typography.h4,
    color: theme.colors.primary,
    fontWeight: '700',
  },
  stateLabel: {
    ...theme.typography.caption,
    color: theme.colors.textSecondary,
    marginTop: 2,
  },
  linkCard: {
    flexDirection: 'row',
    alignItems: 'center',
    padding: theme.spacing.md,
    marginBottom: theme.spacing.md,
    backgroundColor: theme.colors.background,
    borderRadius: theme.borderRadius.md,
    borderWidth: 1,
    borderColor: theme.colors.border,
  },
  linkContent: {
    flexDirection: 'row',
    alignItems: 'center',
    flex: 1,
  },
  linkInfo: {
    flex: 1,
  },
  linkTitle: {
    ...theme.typography.h4,
    color: theme.colors.primary,
    marginBottom: theme.spacing.xs,
  },
  linkDescription: {
    ...theme.typography.bodySmall,
    color: theme.colors.textSecondary,
    marginBottom: theme.spacing.xs,
    lineHeight: 20,
  },
  linkUrl: {
    ...theme.typography.caption,
    color: theme.colors.textLight,
    fontStyle: 'italic',
  },
  errorCard: {
    alignItems: 'center',
    justifyContent: 'center',
    padding: theme.spacing.xxl,
  },
  errorText: {
    ...theme.typography.body,
    color: theme.colors.textSecondary,
    marginTop: theme.spacing.md,
  },
});

export default HWCReportScreen;

