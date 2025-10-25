import "../global.css";

import { Image } from "expo-image";
import { useState } from "react";
import { View, Text, TextInput, FlatList, TouchableOpacity, Alert } from "react-native";
import { Link } from "expo-router";

type Voicemail = {
  id: string;
  number: string;
  name: string;
  description: string;
};

const voicemails: Voicemail[] = [
  { id: "1", number: "+1234567890", name: "Alice", description: "Call about project update" },
  { id: "2", number: "+1987654321", name: "Bob", description: "Missed client call" },
  { id: "3", number: "+1123456789", name: "Charlie", description: "Follow-up meeting" },
];

export default function VoicemailTab() {
  const [search, setSearch] = useState("");
  const [filtered, setFiltered] = useState<Voicemail[]>(voicemails);

  const handleSearch = (text: string) => {
    setSearch(text);
    const newData = voicemails.filter(
      (vm) =>
        vm.name.toLowerCase().includes(text.toLowerCase()) ||
        vm.number.includes(text) ||
        vm.description.toLowerCase().includes(text.toLowerCase())
    );
    setFiltered(newData);
  };

  const renderItem = ({ item }: { item: Voicemail }) => (
    <TouchableOpacity
      className="flex-row bg-white p-4 mx-2 my-1 rounded-lg items-center"
      onPress={() =>
        Alert.alert("Play Voicemail", `Playing voicemail from ${item.name}`)
      }
    >
      <View className="flex-1">
        <Text className="font-bold text-lg">{item.name}</Text>
        <Text className="text-gray-500">{item.number}</Text>
        <Text className="mt-1">{item.description}</Text>
      </View>
    </TouchableOpacity>
  );

  return (
    <View className="flex-1 bg-gray-100">
      <TextInput
        className="bg-white p-3 m-2 rounded-lg text-base"
        placeholder="Search voicemails..."
        value={search}
        onChangeText={handleSearch}
      />
      <FlatList
        data={filtered}
        renderItem={renderItem}
        keyExtractor={(item) => item.id}
        contentContainerStyle={{ paddingBottom: 20 }}
        stickyHeaderIndices={[0]}
      />
    </View>
  );
}
