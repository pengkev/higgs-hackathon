// import React, { useEffect, useRef, useState } from "react";
// import { Modal, View, Text, TouchableOpacity, ActivityIndicator } from "react-native";
// import * as FileSystem from "expo-file-system";
// import { Audio, AVPlaybackStatus } from "expo-av";

// type Props = {
//   visible: boolean;
//   base64: string | null;
//   filename?: string;           // e.g., "12345.wav" (defaults if omitted)
//   onClose: () => void;
// };

// export default function PlayRecordingModal({ visible, base64, filename = "recording.wav", onClose }: Props) {
//   const soundRef = useRef<Audio.Sound | null>(null);
//   const [loading, setLoading] = useState(false);
//   const [isPlaying, setIsPlaying] = useState(false);

//   const recordingsDir = "../output_recordings/";
//   const fileUri = recordingsDir + filename.replace(/[^a-zA-Z0-9._-]/g, "_");

//   async function ensureDir() {
//     const info = await FileSystem.getInfoAsync(recordingsDir);
//     if (!info.exists) {
//       await FileSystem.makeDirectoryAsync(recordingsDir, { intermediates: true });
//     }
//   }



//   async function loadAndPlay() {
//     if (!base64) return;
//     setLoading(true);
//     try {
//       await Audio.setAudioModeAsync({
//         allowsRecordingIOS: false,
//         playsInSilentModeIOS: true, // play even if the ringer is silent
//         staysActiveInBackground: false,
//         shouldDuckAndroid: true,
//         playThroughEarpieceAndroid: false,
//       });

      

//       // Clean any previous sound
//       if (soundRef.current) {
//         await soundRef.current.unloadAsync();
//         soundRef.current.setOnPlaybackStatusUpdate(null);
//         soundRef.current = null;
//       }

//       const { sound } = await Audio.Sound.createAsync(
//         { uri: fileUri },
//         { shouldPlay: true }, // autostart
//         (status: AVPlaybackStatus) => {
//           if (!status.isLoaded) return;
//           setIsPlaying(status.isPlaying);
//           if (status.didJustFinish) {
//             // Auto-close when done (optional)
//             // onClose();
//           }
//         }
//       );

//       soundRef.current = sound;
//     } catch (e) {
//       console.warn("Audio play error:", e);
//     } finally {
//       setLoading(false);
//     }
//   }

//   async function stopAndUnload() {
//     try {
//       if (soundRef.current) {
//         const status = await soundRef.current.getStatusAsync();
//         if (status.isLoaded && status.isPlaying) {
//           await soundRef.current.stopAsync();
//         }
//         await soundRef.current.unloadAsync();
//         soundRef.current.setOnPlaybackStatusUpdate(null);
//         soundRef.current = null;
//       }
//     } catch {}
//   }

//   useEffect(() => {
//     if (visible && base64) {
//       loadAndPlay();
//     }
//     // Cleanup when modal hides or component unmounts
//     return () => {
//       stopAndUnload();
//     };
//     // eslint-disable-next-line react-hooks/exhaustive-deps
//   }, [visible, base64, filename]);

//   const handleTogglePlay = async () => {
//     const snd = soundRef.current;
//     if (!snd) return;
//     const status = await snd.getStatusAsync();
//     if (!status.isLoaded) return;
//     if (status.isPlaying) {
//       await snd.pauseAsync();
//     } else {
//       await snd.playAsync();
//     }
//   };

//   const handleClose = async () => {
//     await stopAndUnload();
//     onClose();
//   };

//   return (
//     <Modal visible={visible} transparent animationType="fade" onRequestClose={handleClose}>
//       <View className="flex-1 bg-black/60 justify-center items-center px-6">
//         <View className="w-full rounded-2xl bg-white p-5">
//           <Text className="text-lg font-semibold mb-2">Playing Recording</Text>
//           <Text className="text-xs text-gray-600 mb-4" numberOfLines={1}>
//             {fileUri}
//           </Text>

//           {loading ? (
//             <View className="flex-row items-center">
//               <ActivityIndicator />
//               <Text className="ml-3">Loading audio…</Text>
//             </View>
//           ) : (
//             <View className="flex-row">
//               <TouchableOpacity
//                 onPress={handleTogglePlay}
//                 className="flex-1 bg-black rounded-xl py-3 items-center mr-2"
//               >
//                 <Text className="text-white font-semibold">{isPlaying ? "Pause" : "Play"}</Text>
//               </TouchableOpacity>

//               <TouchableOpacity
//                 onPress={handleClose}
//                 className="flex-1 bg-gray-200 rounded-xl py-3 items-center ml-2"
//               >
//                 <Text className="font-semibold">Close</Text>
//               </TouchableOpacity>
//             </View>
//           )}
//         </View>
//       </View>
//     </Modal>
//   );
// }
