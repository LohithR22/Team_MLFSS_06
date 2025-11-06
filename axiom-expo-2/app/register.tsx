import React, { useState } from 'react';
import { View, TextInput, Button, Alert, StyleSheet } from 'react-native';

import { useRouter } from 'expo-router';

const RegistrationScreen: React.FC = () => {
  const [name, setName] = useState<string>('');
  const [email, setEmail] = useState<string>('');
  const [phone, setPhone] = useState<string>('');
  const [password, setPassword] = useState<string>('');
  const [address, setAddress] = useState<string>('');
  const router = useRouter();

  const handleRegister = () => {
    console.log('handleRegister called');
    console.log('name:', name);
    console.log('password:', password);
    console.log('address:', address);

    if (!name || !password || !address) {
      Alert.alert('Error', 'Name, password and address are required.');
      return;
    }

    fetch('http://localhost:3000/register', {
      method: 'POST',
      headers: {
        'Content-Type': 'application/json',
      },
      body: JSON.stringify({ name, password, address }),
    })
      .then(response => response.json())
      .then(data => {
        console.log('data:', data);
        if (data.error) {
          Alert.alert('Error', data.error);
        } else {
          Alert.alert('Success', 'Registration successful', [
            { text: 'OK', onPress: () => router.replace('/login') },
          ]);
        }
      })
      .catch(err => {
        Alert.alert('Error', 'Failed to register user.');
        console.log(err);
      });
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
        placeholder="Email"
        onChangeText={setEmail}
        value={email}
      />
      <TextInput
        style={styles.input}
        placeholder="Phone Number"
        onChangeText={setPhone}
        value={phone}
      />
      <TextInput
        style={styles.input}
        placeholder="Password"
        onChangeText={setPassword}
        value={password}
        secureTextEntry
      />
      <TextInput
        style={styles.input}
        placeholder="Address"
        onChangeText={setAddress}
        value={address}
      />
      <Button title="Register" onPress={handleRegister} />
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

export default RegistrationScreen;
