import NextAuth from "next-auth";
import Credentials from "next-auth/providers/credentials";

export type AppRole = "admin" | "analyst" | "viewer";

type DemoUser = {
  id: string;
  name: string;
  email: string;
  password: string;
  role: AppRole;
};

function getDemoUsers(): DemoUser[] {
  return [
    {
      id: "1",
      name: "OmniSight Admin",
      email: process.env.DEMO_ADMIN_EMAIL || "admin@omnisight.local",
      password: process.env.DEMO_ADMIN_PASSWORD || "Admin123!",
      role: "admin",
    },
    {
      id: "2",
      name: "OmniSight Analyst",
      email: process.env.DEMO_ANALYST_EMAIL || "analyst@omnisight.local",
      password: process.env.DEMO_ANALYST_PASSWORD || "Analyst123!",
      role: "analyst",
    },
    {
      id: "3",
      name: "OmniSight Viewer",
      email: process.env.DEMO_VIEWER_EMAIL || "viewer@omnisight.local",
      password: process.env.DEMO_VIEWER_PASSWORD || "Viewer123!",
      role: "viewer",
    },
  ];
}

export const { handlers, signIn, signOut, auth } = NextAuth({
  session: {
    strategy: "jwt",
  },
  pages: {
    signIn: "/login",
  },
  providers: [
    Credentials({
      name: "Credentials",
      credentials: {
        email: { label: "Email", type: "email" },
        password: { label: "Password", type: "password" },
      },
      authorize(credentials) {
        const email = String(credentials?.email || "").trim().toLowerCase();
        const password = String(credentials?.password || "");

        const user = getDemoUsers().find(
          (u) => u.email.toLowerCase() === email && u.password === password
        );

        if (!user) return null;

        return {
          id: user.id,
          name: user.name,
          email: user.email,
          role: user.role,
        };
      },
    }),
  ],
  callbacks: {
    jwt({ token, user }) {
      if (user) {
        token.role = (user as any).role;
        token.name = user.name;
        token.email = user.email;
      }
      return token;
    },
    session({ session, token }) {
      if (session.user) {
        session.user.role = (token.role as AppRole) || "viewer";
        session.user.name = String(token.name || session.user.name || "");
        session.user.email = String(token.email || session.user.email || "");
      }
      return session;
    },
    authorized({ auth, request: { nextUrl } }) {
      const isLoggedIn = !!auth?.user;
      const isPublic =
        nextUrl.pathname.startsWith("/login") ||
        nextUrl.pathname.startsWith("/api/auth") ||
        nextUrl.pathname.startsWith("/_next") ||
        nextUrl.pathname === "/favicon.ico";

      if (isPublic) return true;
      return isLoggedIn;
    },
  },
});