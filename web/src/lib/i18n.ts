// Shared by build-time pages and client scripts.
export const TOPIC_EN: Record<string, string> = {
  politics: 'Politics', crime: 'Crime & courts', sports: 'Sports', entertainment: 'Entertainment',
  business: 'Business & prices', technology: 'Technology', education: 'Education', health: 'Health',
  weather: 'Weather', agriculture: 'Agriculture', devotional: 'Devotional', general: 'General',
};
export const TOPIC_TE: Record<string, string> = {
  politics: 'రాజకీయాలు', crime: 'నేరాలు, కోర్టులు', sports: 'క్రీడలు', entertainment: 'సినిమా',
  business: 'వ్యాపారం, ధరలు', technology: 'టెక్నాలజీ', education: 'విద్య', health: 'ఆరోగ్యం',
  weather: 'వాతావరణం', agriculture: 'వ్యవసాయం', devotional: 'ఆధ్యాత్మికం', general: 'ఇతరాలు',
};
export const TOPIC_ORDER = Object.keys(TOPIC_EN);

export const DISTRICT_TE: Record<string, string> = {
  'Srikakulam': 'శ్రీకాకుళం', 'Vizianagaram': 'విజయనగరం', 'Parvathipuram Manyam': 'పార్వతీపురం మన్యం',
  'Alluri Sitharama Raju': 'అల్లూరి సీతారామరాజు', 'Visakhapatnam': 'విశాఖపట్నం', 'Anakapalli': 'అనకాపల్లి',
  'Kakinada': 'కాకినాడ', 'East Godavari': 'తూర్పు గోదావరి', 'Konaseema': 'కోనసీమ', 'West Godavari': 'పశ్చిమ గోదావరి',
  'Eluru': 'ఏలూరు', 'NTR': 'ఎన్టీఆర్', 'Krishna': 'కృష్ణా', 'Guntur': 'గుంటూరు', 'Palnadu': 'పల్నాడు',
  'Bapatla': 'బాపట్ల', 'Prakasam': 'ప్రకాశం', 'Nellore': 'నెల్లూరు', 'Kurnool': 'కర్నూలు', 'Nandyal': 'నంద్యాల',
  'Anantapur': 'అనంతపురం', 'Sri Sathya Sai': 'శ్రీ సత్యసాయి', 'YSR Kadapa': 'వైఎస్సార్ కడప', 'Annamayya': 'అన్నమయ్య',
  'Chittoor': 'చిత్తూరు', 'Tirupati': 'తిరుపతి',
};

export const KIND_LABEL: Record<string, [string, string]> = {
  leader: ['Leaders', 'నాయకులు'], party: ['Parties', 'పార్టీలు'], topic: ['Topics', 'అంశాలు'], district: ['Districts', 'జిల్లాలు'],
};

export const topicLabel = (t: string): [string, string] => [TOPIC_EN[t] ?? cap(t), TOPIC_TE[t] ?? t];
export const districtLabel = (d: string): [string, string] => [d, DISTRICT_TE[d] ?? d];
const cap = (s: string) => s.charAt(0).toUpperCase() + s.slice(1);

// Schematic tile map: [column, row], roughly north-east at top right, Rayalaseema bottom left.
export const TILE_POS: Record<string, [number, number]> = {
  'Srikakulam': [8, 0], 'Parvathipuram Manyam': [7, 1], 'Vizianagaram': [8, 1],
  'Alluri Sitharama Raju': [6, 2], 'Anakapalli': [7, 2], 'Visakhapatnam': [8, 2],
  'East Godavari': [6, 3], 'Kakinada': [7, 3], 'Eluru': [5, 4], 'West Godavari': [6, 4], 'Konaseema': [7, 4],
  'NTR': [5, 5], 'Krishna': [6, 5], 'Palnadu': [4, 5], 'Guntur': [5, 6], 'Bapatla': [6, 6],
  'Kurnool': [2, 6], 'Nandyal': [3, 6], 'Prakasam': [5, 7], 'Anantapur': [1, 7], 'YSR Kadapa': [3, 7],
  'Sri Sathya Sai': [2, 8], 'Annamayya': [3, 8], 'Nellore': [5, 8], 'Chittoor': [3, 9], 'Tirupati': [4, 9],
};
