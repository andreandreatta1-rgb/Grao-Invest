import { QueryClient, QueryClientProvider } from "@tanstack/react-query";
import { BrowserRouter, Route, Routes } from "react-router-dom";
import { Toaster as Sonner } from "@/components/ui/sonner";
import { Toaster } from "@/components/ui/toaster";
import { TooltipProvider } from "@/components/ui/tooltip";
import MobileShell from "./components/MobileShell";
import Cockpit from "./pages/Cockpit";
import Teses from "./pages/Teses";
import TeseDetalhe from "./pages/TeseDetalhe";
import Lab from "./pages/Lab";
import Mercado from "./pages/Mercado";
import Decisoes from "./pages/Decisoes";
import Configuracao from "./pages/Configuracao";
import Instalar from "./pages/Instalar";
import NotFound from "./pages/NotFound.tsx";

const queryClient = new QueryClient({
  defaultOptions: {
    queries: { staleTime: 5_000, refetchOnWindowFocus: true, retry: 1 },
  },
});

const App = () => (
  <QueryClientProvider client={queryClient}>
    <TooltipProvider>
      <Toaster />
      <Sonner />
      <BrowserRouter>
        <Routes>
          <Route element={<MobileShell />}>
            <Route path="/" element={<Cockpit />} />
            <Route path="/teses" element={<Teses />} />
            <Route path="/teses/:id" element={<TeseDetalhe />} />
            <Route path="/lab" element={<Lab />} />
            <Route path="/mercado" element={<Mercado />} />
            <Route path="/decisoes" element={<Decisoes />} />
            <Route path="/config" element={<Configuracao />} />
            <Route path="/instalar" element={<Instalar />} />
          </Route>
          <Route path="*" element={<NotFound />} />
        </Routes>
      </BrowserRouter>
    </TooltipProvider>
  </QueryClientProvider>
);

export default App;
