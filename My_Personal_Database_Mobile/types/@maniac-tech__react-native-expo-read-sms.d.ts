declare module '@maniac-tech/react-native-expo-read-sms' {
  export function startReadSMS(): Promise<void>;
  export function readSMS(): Promise<any[]>;
}
