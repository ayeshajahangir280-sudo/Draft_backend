export type Category = string;
export type Role = "Batsman" | "Bowler" | "All-Rounder" | "Wicket Keeper";

export type Player = {
  id: string | number;
  name: string;
  category: Category;
  role: Role;
  photo: string;
};

export type Team = {
  id: string | number;
  name: string;
  short: string;
  logo?: string;
};

export const TEAMS: Team[] = [
  { id: "t1", name: "Falcon Warriors", short: "FW" },
  { id: "t2", name: "Yuva Force", short: "YF" },
  { id: "t3", name: "Shuttle Shots", short: "SS" },
  { id: "t4", name: "Asfar Amigos", short: "AA" },
  { id: "t5", name: "Golden Axis Mavericks", short: "GAM" },
  { id: "t6", name: "Team Six", short: "T6" },
  { id: "t7", name: "Team Seven", short: "T7" },
  { id: "t8", name: "Team Eight", short: "T8" },
];

const raw: Array<[string, Category, Role]> = [
  ["Ahmed Khan", "A", "All-Rounder"],
  ["Bilal Ahmed", "A", "Batsman"],
  ["Usman Ali", "A", "Bowler"],
  ["Hassan Raza", "A", "Wicket Keeper"],
  ["Zain Abbas", "A", "Batsman"],
  ["Faisal Iqbal", "A", "Bowler"],
  ["Imran Shah", "B", "All-Rounder"],
  ["Kamran Yousuf", "B", "Batsman"],
  ["Rizwan Malik", "B", "Wicket Keeper"],
  ["Tariq Mehmood", "B", "Bowler"],
  ["Adeel Nawaz", "B", "Batsman"],
  ["Shoaib Anwar", "B", "All-Rounder"],
  ["Junaid Aslam", "C", "Bowler"],
  ["Waqas Haider", "C", "Batsman"],
  ["Noman Sheikh", "C", "All-Rounder"],
  ["Saad Qureshi", "C", "Wicket Keeper"],
  ["Danish Farooq", "C", "Bowler"],
  ["Hamza Tariq", "C", "Batsman"],
  ["Owais Siddiqui", "D", "All-Rounder"],
  ["Rehan Butt", "D", "Bowler"],
  ["Talha Javed", "D", "Batsman"],
  ["Yasir Kamal", "D", "Wicket Keeper"],
  ["Arsalan Ejaz", "D", "Batsman"],
  ["Moiz Hussain", "D", "Bowler"],
];

export const PLAYERS: Player[] = raw.map(([name, category, role], i) => ({
  id: `p${i + 1}`,
  name,
  category,
  role,
  photo: `https://i.pravatar.cc/400?img=${(i % 60) + 11}`,
}));

export const CATEGORIES: Category[] = ["A", "B", "C", "D"];

export function shuffle<T>(arr: T[]): T[] {
  const a = [...arr];
  for (let i = a.length - 1; i > 0; i--) {
    const j = Math.floor(Math.random() * (i + 1));
    [a[i], a[j]] = [a[j] as T, a[i] as T];
  }
  return a;
}
