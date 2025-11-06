import React, { useState } from 'react';
import { View, TextInput, Button, Alert, StyleSheet } from 'react-native';
import * as Location from 'expo-location';

import { useRouter } from 'expo-router';

const LoginScreen: React.FC = () => {
  const [name, setName] = useState<string>('');
  const [password, setPassword] = useState<string>('');
  const router = useRouter();

  const handleLogin = async () => {
    if (!name || !password) {
      Alert.alert('Error', 'Name and password are required.');
      return;
    }

    try {
      const response = await fetch('http://localhost:3000/login', {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json',
        },
        body: JSON.stringify({ name, password }),
      });
      
      const data = await response.json();
      if (data.error) {
        Alert.alert('Error', data.error);
        return;
      }

      // Request location permission and get location
      const { status } = await Location.requestForegroundPermissionsAsync();
      if (status === 'granted') {
        const location = await Location.getCurrentPositionAsync({});
        // Store location in global state or pass via navigation
        // For now, location will be fetched in home.js
      } else {
        Alert.alert('Location Permission', 'Location access is needed for delivery map. You can enable it later in settings.');
      }

      Alert.alert('Success', data.message);
      router.replace('/home');
    } catch (err) {
      Alert.alert('Error', 'Failed to login.');
      console.log(err);
    }
  };

  return (
    <View style={styles.container}>
      <TextInput
        style={styles.input}
        placeholder="Name"
        onChangeText={setName}
        value={name}
      />
      <TextInput
        style={styles.input}
        placeholder="Password"
        onChangeText={setPassword}
        value={password}
        secureTextEntry
      />
      <Button title="Login" onPress={handleLogin} />
      <Button title="Register" onPress={() => router.push('/register')} />
    </View>
  );
};

const styles = StyleSheet.create({
  container: {
    flex: 1,
    justifyContent: 'center',
    alignItems: 'center',
    padding: 16,
  },
  input: {
    width: '100%',
    height: 40,
    borderColor: 'gray',
    borderWidth: 1,
    marginBottom: 12,
    paddingHorizontal: 8,
  },
});

export default LoginScreen;
