// src/types/compare.ts

export interface Cotizacion {
    aseguradora: string;
    plan?: string;
    prima_total?: string;
    tipo_seguro?: string;
    valores?: Record<string, string>;
  }
  
  export interface CompareData {
    campos: string[];
    cotizaciones: Cotizacion[];
    cliente: string;
    periodo_pago?: string;
  }
  