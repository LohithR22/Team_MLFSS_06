import React from 'react';
import { View, StyleSheet } from 'react-native';
import { theme } from '../constants/theme';

const Card = ({ children, style, elevated = true }) => {
  return (
    <View
      style={[
        styles.card,
        elevated && theme.shadows.md,
        style,
      ]}
    >
      {children}
    </View>
  );
};

const styles = StyleSheet.create({
  card: {
    backgroundColor: theme.colors.surface,
    borderRadius: theme.borderRadius.lg,
    padding: theme.spacing.md,
    borderWidth: 1,
    borderColor: theme.colors.border,
  },
});

export default Card;

