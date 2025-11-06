import React, { useState } from 'react';
import { View, TextInput, Button, Alert } from 'react-native';
import { addUser } from '../database/Database';

const RegistrationScreen = () => {
  const [name, setName] = useState('');
  const [email, setEmail] = useState('');
  const [phone, setPhone] = useState('');
  const [password, setPassword] = useState('');
  const [address, setAddress] = useState('');

  const handleRegister = () => {
    if (!name || !password || !address) {
      Alert.alert('Error', 'Name, password and address are required.');
      return;
    }

    addUser(name, password, address)
      .then(() => {
        Alert.alert('Success', 'User registered successfully.');
      })
      .catch(err => {
        Alert.alert('Error', 'Failed to register user.');
        console.log(err);
      });
  };

  return (
    <View>
      <TextInput placeholder="Name" onChangeText={setName} value={name} />
      <TextInput placeholder="Email" onChangeText={setEmail} value={email} />
      <TextInput placeholder="Phone Number" onChangeText={setPhone} value={phone} />
      <TextInput placeholder="Password" onChangeText={setPassword} value={password} secureTextEntry />
      <TextInput placeholder="Address" onChangeText={setAddress} value={address} />
      <Button title="Register" onPress={handleRegister} />
    </View>
  );
};

export default RegistrationScreen;
