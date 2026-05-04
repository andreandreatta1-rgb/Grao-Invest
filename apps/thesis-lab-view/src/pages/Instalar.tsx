import { Apple, Smartphone, Share, Plus, Download, Check } from "lucide-react";
import { usePWA } from "@/hooks/usePWA";
import { Button } from "@/components/ui/button";

export default function Instalar() {
  const { canPrompt, promptInstall, installed, isIOS, isAndroid } = usePWA();

  return (
    <div className="space-y-6 animate-fade-up">
      <header className="rounded-xl bg-gradient-cockpit border border-border/70 p-5 shadow-elevated">
        <p className="text-[11px] uppercase tracking-widest text-muted-foreground mb-1">App</p>
        <h2 className="font-display text-xl font-semibold">Instalar Grão Invest</h2>
        <p className="text-sm text-muted-foreground mt-1">
          Adicione o app à tela de início para abrir como aplicativo, sem barra do navegador.
        </p>
      </header>

      {installed && (
        <div className="rounded-xl border border-validated/40 bg-validated/10 p-4 flex items-center gap-2 text-sm text-validated">
          <Check className="w-4 h-4" /> Já está rodando como app instalado.
        </div>
      )}

      {canPrompt && !installed && (
        <Button onClick={promptInstall} className="w-full" size="lg">
          <Download className="w-4 h-4 mr-2" /> Instalar agora
        </Button>
      )}

      {/* iPhone */}
      <section className="glass-card p-5 space-y-3">
        <div className="flex items-center gap-2">
          <Apple className="w-5 h-5 text-primary" />
          <h3 className="font-display font-semibold">iPhone / iPad</h3>
          {isIOS && <span className="text-[10px] uppercase tracking-widest text-primary ml-auto">seu dispositivo</span>}
        </div>
        <ol className="space-y-2 text-sm text-muted-foreground list-decimal pl-5">
          <li>Abra esta página no <strong className="text-foreground">Safari</strong> (não funciona no Chrome do iOS).</li>
          <li>Toque no ícone <Share className="w-3.5 h-3.5 inline mx-1" /> <strong className="text-foreground">Compartilhar</strong>.</li>
          <li>Escolha <strong className="text-foreground">"Adicionar à Tela de Início"</strong> <Plus className="w-3.5 h-3.5 inline mx-1" />.</li>
          <li>Confirme em <strong className="text-foreground">Adicionar</strong>.</li>
        </ol>
      </section>

      {/* Android */}
      <section className="glass-card p-5 space-y-3">
        <div className="flex items-center gap-2">
          <Smartphone className="w-5 h-5 text-primary" />
          <h3 className="font-display font-semibold">Android</h3>
          {isAndroid && <span className="text-[10px] uppercase tracking-widest text-primary ml-auto">seu dispositivo</span>}
        </div>
        <ol className="space-y-2 text-sm text-muted-foreground list-decimal pl-5">
          <li>Abra esta página no <strong className="text-foreground">Chrome</strong> (ou Edge).</li>
          <li>Toque no menu <strong className="text-foreground">⋮</strong> no canto superior direito.</li>
          <li>Selecione <strong className="text-foreground">"Instalar app"</strong> ou <strong className="text-foreground">"Adicionar à tela inicial"</strong>.</li>
          <li>Confirme — o ícone aparece junto dos seus apps.</li>
        </ol>
      </section>

      <p className="text-[11px] text-muted-foreground text-center px-4">
        O app abre em tela cheia, com barra de status escura e navegação inferior fixa.
        Funciona offline para telas já visitadas; novos dados precisam de conexão.
      </p>
    </div>
  );
}
