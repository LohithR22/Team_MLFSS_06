import React, { useState } from 'react';
import { View, TextInput, Button, Alert } from 'react-native';
import { findUser } from '../database/Database';

const LoginScreen = ({ navigation }) => {
  const [name, setName] = useState('');
  const [password, setPassword] = useState('');

  const handleLogin = () => {
    if (!name || !password) {
      Alert.alert('Error', 'Name and password are required.');
      return;
    }

    findUser(name, password)
      .then(user => {
        if (user) {
          Alert.alert('Success', 'Logged in successfully.');
          navigation.navigate('Home');
        } else {
          Alert.alert('Error', 'Invalid credentials.');
        }
      })
      .catch(err => {
        Alert.alert('Error', 'Failed to login.');
        console.log(err);
      });
  };

  return (
    <View>
      <TextInput placeholder="Name" onChangeText={setName} value={name} />
      <TextInput placeholder="Password" onChangeText={setPassword} value={password} secureTextEntry />
      <Button title="Login" onPress={handleLogin} />
      <Button title="Register" onPress={() => navigation.navigate('Registration')} />
    </View>
  );
};

export default LoginScreen;
