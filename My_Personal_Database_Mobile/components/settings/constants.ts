import { Platform } from 'react-native';
import {
  Smartphone,
  MapPin,
  Heart,
} from 'lucide-react-native';

export const API_URL = process.env.EXPO_PUBLIC_API_URL || 'http://192.168.100.119:8000';

export const integrationItems = [
  { key: 'appleNotes', label: 'APPLE NOTES', image: require('../../assets/images/apple_notes_icon.png'), color: '#ffffff' },
  // All other data sources disabled - only Apple Notes supported
  // { key: 'appleCalendar', label: 'APPLE CALENDAR', image: require('../../assets/images/apple_calendar_icon.png'), color: '#ff3b30' },
  // { key: 'appleMusic', label: 'APPLE MUSIC', image: require('../../assets/images/apple_music_icon.png'), color: '#fa2d48' },
  // ...(Platform.OS === 'ios' ? [{ key: 'iosContacts', label: 'IOS CONTACTS', image: require('../../assets/images/apple_contacts_icon.png'), color: '#007aff' }] : []),
  // ...(Platform.OS === 'android' ? [{ key: 'androidContacts', label: 'ANDROID CONTACTS', icon: Smartphone, color: '#3ddc84' }] : []),
  // ...(Platform.OS === 'ios' ? [{ key: 'iosHealth', label: 'APPLE HEALTH', image: require('../../assets/images/apple_health_icon.png'), color: '#ff3b30' }] : []),
  // ...(Platform.OS === 'android' ? [{ key: 'androidHealth', label: 'GOOGLE FIT', icon: Heart, color: '#4285f4' }] : []),
  // { key: 'locationData', label: 'LOCATION DATA', image: require('../../assets/images/apple_maps_icon.png'), color: '#f59e0b' },
  // { key: 'spotify', label: 'SPOTIFY', image: require('../../assets/images/spotify_icon.png'), color: '#1db954' },
  // { key: 'googleCalendar', label: 'GOOGLE CALENDAR', image: require('../../assets/images/google_calendar_icon.png'), color: '#4285f4' },
  // { key: 'gmail', label: 'GMAIL ARCHIVE', image: require('../../assets/images/gmail_icon.webp'), color: '#ea4335' },
  // { key: 'googleDrive', label: 'GOOGLE DRIVE', image: require('../../assets/images/google_drive_icon.webp'), color: '#34a853' },
  // { key: 'mobileMessages', label: 'MOBILE MESSAGES', image: require('../../assets/images/apple_messages.png'), color: '#9333ea' },
  // { key: 'linkedin', label: 'LINKEDIN', image: require('../../assets/images/linkedin_icon.png'), color: '#0077b5' },
  // { key: 'outlook', label: 'OUTLOOK', image: require('../../assets/images/outlook_icon.png'), color: '#0078d4' },
  // { key: 'github', label: 'GITHUB', image: require('../../assets/images/github_icon.png'), color: '#333333' },
  // { key: 'notion', label: 'NOTION', image: require('../../assets/images/notion_icon.png'), color: '#ffffff' },
  // { key: 'reddit', label: 'REDDIT', image: require('../../assets/images/reddit_icon.png'), color: '#ff4500' },
  // { key: 'youtube', label: 'YOUTUBE', image: require('../../assets/images/youtube_icon.png'), color: '#ff0000' },
  // { key: 'zoom', label: 'ZOOM', image: require('../../assets/images/zoom_icon.png'), color: '#2d8cff' },
  // { key: 'plaid', label: 'PLAID', image: require('../../assets/images/plaid_icon.png'), color: '#2a2a72' },
];

export const defaultIntegrations = {
  appleNotes: false,
  // All other data sources disabled - only Apple Notes supported
  appleCalendar: false,
  appleMusic: false,
  iosContacts: false,
  androidContacts: false,
  iosHealth: false,
  androidHealth: false,
  locationData: false,
  googleCalendar: false,
  gmail: false,
  googleDrive: false,
  mobileMessages: false,
  spotify: false,
  linkedin: false,
  outlook: false,
  github: false,
  notion: false,
  reddit: false,
  youtube: false,
  zoom: false,
  plaid: false,
};
