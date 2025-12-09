import React, { useState } from 'react';
import { Alert, ActivityIndicator, Image, SafeAreaView, ScrollView, StyleSheet, Text, TouchableOpacity, View } from 'react-native';
import { StatusBar } from 'expo-status-bar';
import * as ImagePicker from 'expo-image-picker';

const API_BASE = process.env.EXPO_PUBLIC_API_BASE || 'http://localhost:8000/api';

function formatMacros(macros = {}) {
  const keys = Object.keys(macros || {});
  if (!keys.length) {
    return 'Macros not provided';
  }
  return keys
    .map((key) => `${key.toUpperCase()}: ${Number(macros[key]).toFixed(1)}g`)
    .join(' • ');
}

function ResultCard({ item, onLog, logging }) {
  return (
    <View style={styles.resultCard}>
      <View style={{ flex: 1 }}>
        <Text style={styles.resultTitle}>{item.food.name}</Text>
        <Text style={styles.resultMeta}>{item.food.serving_size}</Text>
        <Text style={styles.resultMeta}>{item.food.calories.toFixed(0)} kcal</Text>
        <Text style={styles.resultMeta}>{formatMacros(item.food.macronutrients)}</Text>
        <Text style={styles.resultConfidence}>Confidence: {(item.confidence * 100).toFixed(0)}%</Text>
      </View>
      <TouchableOpacity
        style={[styles.button, styles.secondaryButton, logging && styles.disabledButton]}
        onPress={() => onLog(item)}
        disabled={logging}
      >
        {logging ? <ActivityIndicator color="#0f172a" /> : <Text style={styles.buttonText}>Log</Text>}
      </TouchableOpacity>
    </View>
  );
}

export default function App() {
  const [image, setImage] = useState(null);
  const [results, setResults] = useState([]);
  const [scanning, setScanning] = useState(false);
  const [loggingName, setLoggingName] = useState(null);

  const requestCameraPermission = async () => {
    const { status } = await ImagePicker.requestCameraPermissionsAsync();
    if (status !== 'granted') {
      Alert.alert('Permission needed', 'Camera access is required to scan food.');
      return false;
    }
    return true;
  };

  const requestLibraryPermission = async () => {
    const { status } = await ImagePicker.requestMediaLibraryPermissionsAsync();
    if (status !== 'granted') {
      Alert.alert('Permission needed', 'Photo library access is required to choose a picture.');
      return false;
    }
    return true;
  };

  const captureImage = async () => {
    const granted = await requestCameraPermission();
    if (!granted) return;
    const result = await ImagePicker.launchCameraAsync({
      base64: true,
      quality: 0.6,
      allowsEditing: false,
    });
    if (!result.canceled) {
      setImage(result.assets[0]);
      setResults([]);
    }
  };

  const pickImage = async () => {
    const granted = await requestLibraryPermission();
    if (!granted) return;
    const result = await ImagePicker.launchImageLibraryAsync({
      base64: true,
      quality: 0.6,
      allowsEditing: false,
    });
    if (!result.canceled) {
      setImage(result.assets[0]);
      setResults([]);
    }
  };

  const scanImage = async () => {
    if (!image?.base64) {
      Alert.alert('No image selected', 'Capture or choose a photo first.');
      return;
    }
    setScanning(true);
    try {
      const response = await fetch(`${API_BASE}/foods/scan-image`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({
          image_base64: image.base64,
          top_k: 3,
        }),
      });
      if (!response.ok) {
        const detail = await response.text();
        throw new Error(detail || 'Scan failed');
      }
      const data = await response.json();
      setResults(data.items || []);
    } catch (error) {
      Alert.alert('Scan failed', error.message);
    } finally {
      setScanning(false);
    }
  };

  const logFood = async (item) => {
    setLoggingName(item.food.name);
    try {
      const response = await fetch(`${API_BASE}/entries`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ food: item.food, quantity: 1 }),
      });
      if (!response.ok) {
        const detail = await response.text();
        throw new Error(detail || 'Logging failed');
      }
      Alert.alert('Logged', `${item.food.name} added to your log.`);
    } catch (error) {
      Alert.alert('Log failed', error.message);
    } finally {
      setLoggingName(null);
    }
  };

  return (
    <SafeAreaView style={styles.safeArea}>
      <StatusBar style="light" />
      <ScrollView contentContainerStyle={styles.container}>
        <Text style={styles.heading}>Food Tracker (Mobile)</Text>
        <Text style={styles.subtitle}>Capture a meal, let AI estimate macros, then log it.</Text>

        <View style={styles.previewCard}>
          {image?.uri ? (
            <Image source={{ uri: image.uri }} style={styles.preview} />
          ) : (
            <Text style={styles.previewPlaceholder}>No image selected</Text>
          )}
        </View>

        <View style={styles.buttonRow}>
          <TouchableOpacity style={styles.button} onPress={captureImage}>
            <Text style={styles.buttonText}>Take photo</Text>
          </TouchableOpacity>
          <TouchableOpacity style={styles.button} onPress={pickImage}>
            <Text style={styles.buttonText}>Choose from library</Text>
          </TouchableOpacity>
        </View>

        <TouchableOpacity
          style={[styles.button, styles.primaryButton, scanning && styles.disabledButton]}
          onPress={scanImage}
          disabled={scanning}
        >
          {scanning ? <ActivityIndicator color="#0f172a" /> : <Text style={styles.buttonText}>Scan image</Text>}
        </TouchableOpacity>

        <View style={styles.resultsContainer}>
          <Text style={styles.sectionTitle}>AI suggestions</Text>
          {!results.length && <Text style={styles.resultMeta}>No results yet. Capture a photo and tap Scan.</Text>}
          {results.map((item) => (
            <ResultCard
              key={`${item.food.name}-${item.food.serving_size}`}
              item={item}
              onLog={logFood}
              logging={loggingName === item.food.name}
            />
          ))}
        </View>
      </ScrollView>
    </SafeAreaView>
  );
}

const styles = StyleSheet.create({
  safeArea: {
    flex: 1,
    backgroundColor: '#0f172a',
  },
  container: {
    padding: 16,
    gap: 12,
  },
  heading: {
    fontSize: 24,
    fontWeight: '700',
    color: '#e2e8f0',
  },
  subtitle: {
    color: '#cbd5e1',
    marginBottom: 8,
  },
  previewCard: {
    borderRadius: 16,
    borderWidth: 1,
    borderColor: 'rgba(148, 163, 184, 0.3)',
    backgroundColor: 'rgba(30, 41, 59, 0.65)',
    padding: 12,
    minHeight: 200,
    justifyContent: 'center',
    alignItems: 'center',
  },
  preview: {
    width: '100%',
    height: 260,
    borderRadius: 12,
  },
  previewPlaceholder: {
    color: '#94a3b8',
  },
  buttonRow: {
    flexDirection: 'row',
    gap: 12,
    flexWrap: 'wrap',
  },
  button: {
    flex: 1,
    paddingVertical: 14,
    borderRadius: 12,
    alignItems: 'center',
    backgroundColor: '#334155',
    borderWidth: 1,
    borderColor: 'rgba(148, 163, 184, 0.3)',
  },
  primaryButton: {
    backgroundColor: '#38bdf8',
  },
  secondaryButton: {
    backgroundColor: '#22d3ee',
    minWidth: 88,
  },
  disabledButton: {
    opacity: 0.6,
  },
  buttonText: {
    color: '#0f172a',
    fontWeight: '700',
  },
  resultsContainer: {
    marginTop: 8,
    gap: 8,
  },
  sectionTitle: {
    color: '#e2e8f0',
    fontSize: 18,
    fontWeight: '600',
  },
  resultCard: {
    flexDirection: 'row',
    gap: 12,
    padding: 12,
    borderRadius: 12,
    borderWidth: 1,
    borderColor: 'rgba(148, 163, 184, 0.3)',
    backgroundColor: 'rgba(30, 41, 59, 0.7)',
    alignItems: 'center',
  },
  resultTitle: {
    color: '#e2e8f0',
    fontSize: 16,
    fontWeight: '600',
  },
  resultMeta: {
    color: '#cbd5e1',
    marginTop: 2,
  },
  resultConfidence: {
    color: '#38bdf8',
    marginTop: 4,
    fontWeight: '600',
  },
});
