"use client";

import { useEffect, useState } from "react";
import { ServerCrash, RefreshCw } from "lucide-react";
import { TooltipProvider } from "@/components/ui/tooltip";
import { Button } from "@/components/ui/button";
import { useDesignStore } from "@/store/design-store";
import { API_BASE } from "@/lib/api";
import { TopBar } from "./TopBar";
import { EmptyState } from "./EmptyState";
import { AddFloorPlanDialog } from "./AddFloorPlanDialog";
import { DeviceToolbar } from "./DeviceToolbar";
import { WorkspaceToolbar } from "./WorkspaceToolbar";
import { Canvas } from "./Canvas";
import { InspectorPanel } from "./InspectorPanel";
import { CalibrateDialog } from "./CalibrateDialog";

export function DesignTool() {
  const floors = useDesignStore((s) => s.project.floors);
  const hydrated = useDesignStore((s) => s.hydrated);
  const serverError = useDesignStore((s) => s.serverError);
  const projectId = useDesignStore((s) => s.projectId);
  const init = useDesignStore((s) => s.init);
  const [addOpen, setAddOpen] = useState(false);

  useEffect(() => {
    void init();
  }, [init]);

  const hasFloors = floors.length > 0;

  return (
    <TooltipProvider>
      <div className="flex h-screen flex-col overflow-hidden bg-background text-foreground">
        <TopBar onAddFloor={() => setAddOpen(true)} />
        {!hydrated ? (
          <div className="flex flex-1 items-center justify-center text-sm text-muted-foreground">
            Memuat proyek dari server...
          </div>
        ) : serverError && !projectId ? (
          <div className="flex flex-1 items-center justify-center p-8">
            <div className="flex max-w-lg flex-col items-center text-center">
              <div className="mb-4 flex size-20 items-center justify-center rounded-full bg-muted">
                <ServerCrash className="size-9 text-[#c9cdd4]" strokeWidth={1.5} />
              </div>
              <h2 className="text-base font-semibold">Backend belum berjalan</h2>
              <p className="mt-2 text-sm text-muted-foreground">{serverError}</p>
              <p className="mt-3 rounded-md bg-muted px-3 py-2 font-mono text-xs">
                cd backend &amp;&amp; python server.py &nbsp;→&nbsp; {API_BASE}
              </p>
              <Button className="btn-primary-vigi mt-5" onClick={() => void init()}>
                <RefreshCw /> Coba lagi
              </Button>
            </div>
          </div>
        ) : !hasFloors ? (
          <EmptyState onAdd={() => setAddOpen(true)} />
        ) : (
          <div className="flex min-h-0 min-w-0 flex-1">
            <DeviceToolbar />
            <div className="flex min-w-0 flex-1 flex-col">
              <WorkspaceToolbar onAddFloor={() => setAddOpen(true)} />
              <Canvas />
            </div>
            <InspectorPanel />
          </div>
        )}
        <AddFloorPlanDialog open={addOpen} onOpenChange={setAddOpen} />
        <CalibrateDialog />
      </div>
    </TooltipProvider>
  );
}
