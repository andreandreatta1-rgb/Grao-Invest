from __future__ import annotations

import csv
import json
from pathlib import Path

from app.services.b3_data_lake import (
    _parse_locale_int,
    _parse_locale_number,
    run_b3_bronze_silver_pipeline,
)


def _write(path: Path, content: str) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(content, encoding="latin1")


def test_locale_parsers_handle_b3_number_patterns() -> None:
    assert _parse_locale_number("1.234.567,89") == 1234567.89
    assert _parse_locale_number("0,00") == 0.0
    assert _parse_locale_number("") == ""
    assert _parse_locale_int("1.234") == 1234
    assert _parse_locale_int("12,0") == 12
    assert _parse_locale_int("") == ""


def test_b3_bronze_silver_pipeline_builds_expected_outputs(tmp_path: Path) -> None:
    source_root = tmp_path / "historico_2026-04-22"
    output_root = tmp_path / "lake" / "b3"
    pesquisa_root = tmp_path / "pesquisa_pregao_2026-04-22"

    cotahist_line = (
        "012026042002SANB11      010SANTANDER BRUNT          R$  "
        "000000000316200000000031710000000003137000000000315400000000031600000000003158"
        "00000000031601028100000000000311310000000000982165690000000000000000999912310000"
        "0010000000000000BRSANBCDAM13172"
    )
    cotahist_payload = (
        "00COTAHIST.2026BOVESPA 20260420\n"
        f"{cotahist_line}\n"
        f"99{'0' * 243}\n"
    )
    _write(
        source_root / "extracted" / "COTAHIST_D20042026" / "COTAHIST_D20042026.TXT",
        cotahist_payload,
    )

    _write(
        source_root
        / "cambio"
        / "extracted"
        / "Cambio_Parametros de Abertura_01.2024"
        / "Parametros de Abertura_2024.01.txt",
        (
            "Data de Contratacao;Data de Liquidacao;Taxa de Abertura;Cenario de Stress %;\n"
            "20240102;20240103;4,8366;12;\n"
        ),
    )
    _write(
        source_root
        / "cambio"
        / "extracted"
        / "Cambio_Retroativo_01.2024"
        / "Cambio Retroativo Por Dia_2024.01.txt",
        (
            "Moeda;Data de Contratacao;Data de Liquidacao;Taxa Minima;Taxa Maxima;"
            "Taxa de Fechamento;TCAM;Volume Contratado USD;Volume Contratado BRL;"
            "Volume Liquidado USD;Volume Liquidado BRL;Quantidade de Negocios;"
            "Cenario de Stress %;Taxa de Abertura;\n"
            "USD;20240102;20240103;4,8595;4,9174;4,8998;4,8972;374905907,97;1835995500,69;"
            "334485907,97;1638175168,69;24;12;4,8366;\n"
        ),
    )
    _write(
        source_root
        / "cambio"
        / "extracted"
        / "Cambio_Retroativo_01.2024"
        / "Cambio Dados Por Canal De Negociacao_2024.01.txt",
        (
            "Data;Prazo;V1;V2;V3;V4;V5;V6;Q1;Q2;Q3;TMin1;TMed1;TMax1;TMin2;TMed2;TMax2;\n"
            "20240102;1;10,00;20,00;0,00;0,00;10,00;20,00;2;0;2;4,8000;4,8500;4,9000;"
            "0,0000;0,0000;0,0000;\n"
        ),
    )
    _write(
        source_root
        / "cambio"
        / "extracted"
        / "Cambio_Retroativo_01.2024"
        / "Cambio Volumes Contratados Medias Diarias_2024.01.txt",
        (
            "Mes-Ano;A;B;C;D;E;F;\n"
            "Apr-23;0,00;0,00;2148336385,47;10780456531,90;2148336385,47;10780456531,90;\n"
        ),
    )

    (source_root / "cambio" / "api_snapshots").mkdir(parents=True, exist_ok=True)
    (source_root / "cambio" / "api_snapshots" / "retroativo_getlist_2026-04-22.json").write_text(
        json.dumps(
            {
                "results": [
                    {
                        "transactions": [
                            {
                                "dataContratacao": "22/04/2026",
                                "dataLiquidacao": "23/04/2026",
                                "valorUltimaTaxa": "4,9663",
                                "valorLiquidadoMoedaEstrangeira": "1.102.980.624,20",
                                "valorLiquidadoMoedaBase": "5.486.548.072,42",
                                "valorNegociadoMoedaEstrangeiraDiaTotal": "949.905.899,87",
                                "valorNegociadoMoedaBaseDiaTotal": "4.716.293.377,42",
                                "quantidadeRegistroDiaTotal": "49",
                                "otc": {
                                    "valorTaxaMedia": "4,9650",
                                    "valorMenorTaxa": "4,9563",
                                    "valorMaiorTaxa": "4,9876",
                                    "valorNegociadoMoedaEstrangeira": "949.905.899,87",
                                    "valorNegociadoMoedaBase": "4.716.293.377,42",
                                },
                            }
                        ]
                    }
                ]
            }
        ),
        encoding="utf-8",
    )
    (source_root / "cambio" / "api_snapshots" / "resumos_getlist_2026-04-22.json").write_text(
        json.dumps(
            {
                "summaries": [
                    {
                        "dataContratacao": "10:00",
                        "dataLiquidacao": "24/04/2026",
                        "quantidadeTotalRegistro": "15",
                        "valorTaxaMedia": "4,9691",
                        "valorMenorTaxa": "4,9614",
                        "valorMaiorTaxa": "4,9880",
                        "valorTotalNegociadoMoedaBase": "2.993.230.250,0000",
                        "valorTotalNegociadoMoedaEstrangeira": "602.000.000,00",
                    }
                ]
            }
        ),
        encoding="utf-8",
    )
    (source_root / "cambio" / "api_snapshots" / "parametros_getlist_2026-04-22.json").write_text(
        json.dumps(
            {
                "results": [
                    {
                        "dataContratacao": "22/04/2026",
                        "dataLiquidacao": "23/04/2026",
                        "valTaxaAbertura": "4,9781",
                        "valCenarioStress": "12,0000",
                    }
                ]
            }
        ),
        encoding="utf-8",
    )

    _write(
        source_root / "renda_fixa" / "raw" / "ADA_Estoque_301097_a_211207.csv",
        "Data;Volume em R$;;;;;;;\n30/10/1997;1990795393;;;;;;;\n",
    )
    _write(
        source_root / "renda_fixa" / "raw" / "ADA_Volume_011099_a_271106.csv",
        "Data;Total - Nr. Op.;Total - Volume\n01/10/1999;2;79359,03\n",
    )

    _write(
        pesquisa_root
        / "extracted"
        / "PR260422"
        / "PR260422"
        / "BVBG.086.01_TESTE.xml",
        "<root />\n",
    )

    payload = run_b3_bronze_silver_pipeline(
        source_root=source_root,
        output_root=output_root,
        instruments=["SANB11"],
        include_all_instruments=False,
        pesquisa_root=pesquisa_root,
    )

    assert payload["datasets"]["cotahist"]["silver_rows"] == 1
    assert payload["datasets"]["cambio"]["input_files"] == 4
    assert payload["datasets"]["renda_fixa"]["silver_rows"] == 2
    assert payload["datasets"]["pesquisa_pregao"]["input_files"] == 1

    market_daily = output_root / "silver" / "market_daily.csv"
    with market_daily.open("r", encoding="utf-8", newline="") as file:
        rows = list(csv.DictReader(file))
    assert len(rows) == 1
    assert rows[0]["instrument"] == "SANB11"
    assert rows[0]["trade_date"] == "2026-04-20"

    cambio_api = output_root / "silver" / "cambio_api_retroativo.csv"
    with cambio_api.open("r", encoding="utf-8", newline="") as file:
        api_rows = list(csv.DictReader(file))
    assert len(api_rows) == 1
    assert api_rows[0]["trade_count_total"] == "49"

    pesquisa_manifest = output_root / "bronze" / "pesquisa_pregao" / "files_manifest.csv"
    with pesquisa_manifest.open("r", encoding="utf-8", newline="") as file:
        manifest_rows = list(csv.DictReader(file))
    assert len(manifest_rows) == 1
    assert manifest_rows[0]["layout_code"] == "BVBG.086.01"
