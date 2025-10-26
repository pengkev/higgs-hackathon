import "../global.css";
import api from "../api.js";
import { Buffer } from "buffer";
import  AudioOverlay  from "./play";
import { useState, useEffect } from "react";
import {
  View,
  Text,
  TextInput,
  FlatList,
  TouchableOpacity,
  Image,
} from "react-native";

export type Voicemail = {
  id: string;
  number: string;
  name: string;
  description: string;
  spam: boolean;
  date: Date;
  unread: boolean;
  recording: string | null;
};

export default function VoicemailTab() {
  const [search, setSearch] = useState("");
  const [voicemails, setVoicemails] = useState<Voicemail[]>([]);
  const [filtered, setFiltered] = useState<Voicemail[]>([]);
  const [filterSpam, setFilterSpam] = useState(false);
  const [filterUnread, setFilterUnread] = useState(true);
  const [showSplash, setShowSplash] = useState(true);
  const [recording, setRecording] = useState<string | null>(null);
  const [modal, setModal] = useState(false);

  const handleRecording = async ({ item }: { item: Voicemail }) => {
    try {
      const updated = { ...item, unread: false };
      const res = await api.put("/voicemails", updated, {
        responseType: "arraybuffer",
      });

      setVoicemails((curr) =>
        curr.map((v) => (v.id === item.id ? { ...v, unread: false } : v))
      );  
      const base64 = Buffer.from(res.data, "binary").toString("base64");
     
      return base64;


      console.log(base64);
    } catch (error) {
      console.error("Error adding voicemail", error);
    }
  };

  useEffect(() => {
    const fetchVoicemails = async () => {
      try {
        const res = await api.get("/voicemails");
        const voicemails = res.data.voicemails.map((vm: Voicemail) => ({
          ...vm,
          date: new Date(vm.date),
        }));
        setVoicemails(voicemails);
      } catch (error) {
        console.error("Error fetching voicemails", error);
      }
    };
    fetchVoicemails();
  }, []);

  useEffect(() => {
    // Hide splash screen after 2 seconds
    const timer = setTimeout(() => {
      setShowSplash(false);
    }, 2000);
    return () => clearTimeout(timer);
  }, []);

  const handleSearch = (text: string) => {
    setSearch(text);
  };

  useEffect(() => {
    const newData = voicemails.filter((vm: Voicemail) => {
      if (filterUnread && !vm.unread) return false;
      if (filterSpam) {
        return (
          (vm.name.toLowerCase().includes(search.toLowerCase()) ||
            vm.number.includes(search) ||
            vm.description.toLowerCase().includes(search.toLowerCase())) &&
          vm.spam
        );
      } else {
        return (
          (vm.name.toLowerCase().includes(search.toLowerCase()) ||
            vm.number.includes(search) ||
            vm.description.toLowerCase().includes(search.toLowerCase())) &&
          !vm.spam
        );
      }
    });
    setFiltered(newData);
  }, [filterSpam, filterUnread, search, voicemails]);

  // Splash Screen
  if (showSplash) {
    return (
      <View className="flex-1 bg-white items-center justify-center">
        <Image
          source={require("../assets/images/splash-icon.png")}
          className="w-48 h-48"
          resizeMode="contain"
        />
        <Text className="text-2xl font-bold text-fern_green mt-4">
          HiggsCeptionist
        </Text>
      </View>
    );
  }
  
  const renderItem = ({ item }: { item: Voicemail }) => (
    <TouchableOpacity
      className="flex-row bg-white p-4 mx-2 my-1 rounded-lg items-center relative"
      onPress={async () => {
        try {
          const base64 = await handleRecording({ item }); 
          setRecording(base64 || null);
          setModal(true);
        } catch (e) {
          console.error(e);
        }
      }}
    >
      {item.unread && (
        <View className="absolute top-2 left-2 w-3 h-3 bg-blue-500 rounded-full" />
      )}
      <View className="flex-1 flex-row items-center">
        <View className="flex-[2]">
          <Text className="font-bold text-lg">{item.number}</Text>
          <Text className="text-gray-500">{item.name}</Text>
          <Text className="mt-1">{item.description}</Text>
        </View>

        <View className="flex-[1] items-end">
          <Text className="font-bold text-md">
            {item.date.toLocaleDateString(undefined, {
              year: "numeric",
              month: "2-digit",
              day: "2-digit",
            })}
          </Text>
          <Text className="text-gray-400 text-sm">
            {item.date.toLocaleTimeString([], {
              hour: "2-digit",
              minute: "2-digit",
            })}
          </Text>
        </View>
      </View>
    </TouchableOpacity>
  );

  return (
    <View className="flex-1 bg-gray-100 dark:bg-black">
      <TextInput
        className="bg-white border border-black p-3 mt-10 m-3 rounded-lg text-base"
        placeholder="Search voicemails..."
        value={search}
        onChangeText={handleSearch}
      />
      <View className="flex-row justify-around m-3">
        <TouchableOpacity
          className={`mx-1 flex-1 rounded-lg py-3 items-center ${
            filterUnread ? "bg-fern_green" : "bg-charcoal"
          }`}
          onPress={() => setFilterUnread(!filterUnread)}
        >
          <Text className="text-white font-semibold">Unread</Text>
        </TouchableOpacity>
        <TouchableOpacity
          className={`mx-1 flex-1 rounded-lg py-3 items-center ${
            filterSpam ? "bg-mantis" : "bg-charcoal"
          }`}
          onPress={() => setFilterSpam(!filterSpam)}
        >
          <Text className="text-white font-semibold">Spam</Text>
        </TouchableOpacity>
      </View>

      <FlatList
        data={[...filtered].sort((a, b) => b.date.getTime() - a.date.getTime())}
        renderItem={renderItem}
        keyExtractor={(item) => item.id}
        contentContainerStyle={{ paddingBottom: 20 }}
      />
      {modal && recording && (
        <AudioOverlay
          base64={recording}
          visible
          onClose={() => {
            setModal(false);
            setRecording(null);
          }}
        />
      )}
    </View>
  );
}
