import { ProfileForm } from "@/components/profile/ProfileForm";

export default function ProfilePage() {
  return (
    <div>
      <h1 className="text-xl font-semibold mb-1">Developer Profile</h1>
      <p className="text-slate-400 mb-6 text-sm">
        Tell us who you are so issue and repo scoring can be calibrated to you.
      </p>
      <ProfileForm />
    </div>
  );
}
