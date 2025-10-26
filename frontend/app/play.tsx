import React, { useEffect, useMemo, useRef, useState } from "react";
import { MaterialIcons } from "@expo/vector-icons";

import {
  Pressable,
  TouchableOpacity,
  Text,
  ActivityIndicator,
  Platform,
} from "react-native";
import * as FileSystem from "expo-file-system/legacy";
import { useAudioPlayer } from "expo-audio";

type Props = {
  base64: string;
  visible?: boolean;
  onClose?: () => void;
};

export default function AudioOverlay({
  base64,
  visible = true,
  onClose,
}: Props) {
  const [uri, setUri] = useState<string | null>(null);
  const [loading, setLoading] = useState(true);
  const [isPlaying, setIsPlaying] = useState(false);

  const lastUriRef = useRef<string | null>(null);

  // keep raw base64 for native FS writes
  const strippedBase64 = useMemo(
    () =>
      base64 ? base64.replace(/^data:audio\/[a-zA-Z0-9.+-]+;base64,/, "") : "",
    [base64]
  );

  // Create a playable URI from base64:
  // - native: write a temp .wav to cacheDirectory
  // - web: create a Blob URL
  useEffect(() => {
    let cancelled = false;

    (async () => {
      try {
        setLoading(true);

        // Cleanup previous resource
        if (lastUriRef.current) {
          if (Platform.OS === "web") {
            URL.revokeObjectURL(lastUriRef.current);
          } else {
            try {
              await FileSystem.deleteAsync(lastUriRef.current, {
                idempotent: true,
              });
            } catch {}
          }
          lastUriRef.current = null;
        }

        if (!base64) {
          if (!cancelled) setUri(null);
          return;
        }

        if (Platform.OS === "web") {
          // If a full data: URL was provided, prefer to use it directly.
          if (base64.startsWith("data:audio/")) {
            if (!cancelled) {
              setUri(base64);
              lastUriRef.current = base64; // (no revoke needed for data: URIs)
            }
            return;
          }
          // Otherwise build a Blob URL from the stripped base64
          const byteChars = atob(strippedBase64);
          const bytes = new Uint8Array(byteChars.length);
          for (let i = 0; i < byteChars.length; i++)
            bytes[i] = byteChars.charCodeAt(i);
          const blob = new Blob([bytes], { type: "audio/wav" });
          const url = URL.createObjectURL(blob);
          if (!cancelled) {
            setUri(url);
            lastUriRef.current = url; // revoke later
          }
        } else {
          // Native: write a temp file under cacheDirectory
          const dir = FileSystem.cacheDirectory + "audio/";
          await FileSystem.makeDirectoryAsync(dir, {
            intermediates: true,
          }).catch(() => {});
          const outUri = `${dir}audio_${Date.now()}.wav`;
          await FileSystem.writeAsStringAsync(outUri, strippedBase64, {
            encoding: FileSystem.EncodingType.Base64,
          });
          if (!cancelled) {
            setUri(outUri);
            lastUriRef.current = outUri;
          }
        }
      } catch (e) {
        console.error("Failed to create WAV file/URL:", e);
        if (!cancelled) setUri(null);
      } finally {
        if (!cancelled) setLoading(false);
      }
    })();

    return () => {
      cancelled = true;
    };
  }, [base64, strippedBase64]);

  // Player
  const player = useAudioPlayer(uri ?? undefined);

  //   // Cleanup on unmount
  //   useEffect(() => {
  //     return () => {
  //       (async () => {
  //         try { await player?.unloadAsync?.(); } catch {}
  //         if (lastUriRef.current) {
  //           if (Platform.OS === "web") {
  //             if (lastUriRef.current.startsWith("blob:")) URL.revokeObjectURL(lastUriRef.current);
  //           } else {
  //             try { await FileSystem.deleteAsync(lastUriRef.current, { idempotent: true }); } catch {}
  //           }
  //           lastUriRef.current = null;
  //         }
  //       })();
  //     };
  //   }, [player]);

  if (!visible) return null;

  const toggle = () => {
    if (!player) return;
    player.playing ? player.pause() : player.play();
    setIsPlaying(player.playing);
  };

  return (
    <Pressable
      className="absolute inset-0 z-[9999] items-center justify-center bg-black/70"
      onPress={onClose}
    >
      {loading ? (
        <ActivityIndicator size="large" />
      ) : (
        // stop propagation so clicking the button doesn’t close the overlay
        <TouchableOpacity
          activeOpacity={0.8}
          className="w-24 h-24 rounded-full bg-white items-center justify-center shadow"
          onPress={(e) => {
            e.stopPropagation();
            toggle();
          }}
          disabled={!uri}
        >
          <MaterialIcons
            name={isPlaying ? "pause" : "play-arrow"}
            size={48}
            color="black"
          />
        </TouchableOpacity>
      )}
    </Pressable>
  );
}
