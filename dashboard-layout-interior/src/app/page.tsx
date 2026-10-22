import { DesignTool } from "@/components/design/DesignTool";
import { AuthGate } from "@/components/auth/AuthGate";

export default function Home() {
  return (
    <AuthGate>
      <DesignTool />
    </AuthGate>
  );
}
