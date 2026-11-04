(() => {
    const form = document.getElementById("form-venda");
    const busca = document.getElementById("busca-produto");
    const resultados = document.getElementById("busca-resultados");
    const aviso = document.getElementById("busca-aviso");
    const lista = document.getElementById("carrinho");
    const vazio = document.getElementById("carrinho-vazio");
    const campoItens = form.elements.itens;
    const moeda = new Intl.NumberFormat("pt-BR", { style: "currency", currency: "BRL" });

    let carrinho = campoItens.value ? JSON.parse(campoItens.value) : [];
    let ultimaBusca = 0;
    let temporizador;

    const centavos = (valor) => Math.round(Number(valor) * 100);
    const reais = (valor) => (valor / 100).toFixed(2);

    const elemento = (tag, classes, texto) => {
        const criado = document.createElement(tag);
        criado.className = classes;
        if (texto !== undefined) {
            criado.textContent = texto;
        }
        return criado;
    };

    const unidadesNoCarrinho = (produto) =>
        carrinho
            .filter((item) => item.produto === produto)
            .reduce((total, item) => total + item.quantidade * item.fator, 0);

    const valorPadrao = (item) => reais(centavos(item.preco) * item.fator * item.quantidade);

    const atualizarResumo = () => {
        const subtotal = carrinho.reduce((total, item) => total + centavos(item.valor_total), 0);
        const desconto = centavos(form.elements.desconto.value || 0);
        document.getElementById("resumo-subtotal").textContent = moeda.format(subtotal / 100);
        document.getElementById("resumo-total").textContent = moeda.format(Math.max(subtotal - desconto, 0) / 100);
        campoItens.value = JSON.stringify(carrinho);
    };

    const campoNumero = (rotulo, valor, atributos, aoMudar) => {
        const caixa = elemento("label", "block text-sm");
        caixa.append(elemento("span", "mb-1 block opacity-70", rotulo));
        const campo = elemento("input", "input w-full");
        Object.assign(campo, { type: "number", value: valor, ...atributos });
        campo.addEventListener("input", () => aoMudar(campo));
        caixa.append(campo);
        return caixa;
    };

    const desenhar = () => {
        lista.replaceChildren();
        vazio.hidden = carrinho.length > 0;

        carrinho.forEach((item, indice) => {
            const linha = elemento("li", "rounded-box border border-base-300 p-3");
            const topo = elemento("div", "mb-2 flex items-start justify-between gap-3");
            const titulo = elemento("div", "");
            titulo.append(elemento("p", "font-semibold", item.nome));
            titulo.append(elemento("p", "text-sm opacity-70", item.embalagem
                ? `${item.embalagem_nome} (${item.fator} unidades)`
                : "Unidade"));
            const remover = elemento("button", "btn btn-ghost btn-sm", "Remover");
            remover.type = "button";
            remover.addEventListener("click", () => {
                carrinho.splice(indice, 1);
                desenhar();
            });
            topo.append(titulo, remover);

            const excesso = elemento("p", "mt-2 hidden text-sm text-error");
            const conferirSaldo = () => {
                const faltando = unidadesNoCarrinho(item.produto) > item.saldo;
                excesso.classList.toggle("hidden", !faltando);
                excesso.textContent = `Estoque disponível: ${item.saldo}.`;
            };

            const valor = campoNumero("Valor", item.valor_total, { min: "0", step: "0.01" }, (campo) => {
                item.valor_total = campo.value || "0";
                item.valor_editado = true;
                atualizarResumo();
            });
            const quantidade = campoNumero("Quantidade", item.quantidade, { min: "1", step: "1" }, (campo) => {
                item.quantidade = Math.max(Number(campo.value) || 1, 1);
                if (!item.valor_editado) {
                    item.valor_total = valorPadrao(item);
                    valor.querySelector("input").value = item.valor_total;
                }
                conferirSaldo();
                atualizarResumo();
            });
            const campos = elemento("div", "grid grid-cols-2 gap-3");
            campos.append(quantidade, valor);

            linha.append(topo, campos, excesso);
            lista.append(linha);
            conferirSaldo();
        });

        atualizarResumo();
    };

    const adicionar = (produto, embalagem = null) => {
        const repetido = carrinho.find(
            (item) => item.produto === produto.id && item.embalagem === (embalagem ? embalagem.id : null)
        );
        if (repetido) {
            repetido.quantidade += 1;
            if (!repetido.valor_editado) {
                repetido.valor_total = valorPadrao(repetido);
            }
        } else {
            const item = {
                produto: produto.id,
                nome: produto.nome,
                preco: produto.preco,
                saldo: produto.saldo,
                embalagem: embalagem ? embalagem.id : null,
                embalagem_nome: embalagem ? embalagem.tipo : "",
                fator: embalagem ? embalagem.fator : 1,
                quantidade: 1,
            };
            item.valor_total = valorPadrao(item);
            carrinho.push(item);
        }

        busca.value = "";
        resultados.replaceChildren();
        mostrarAviso("");
        desenhar();
        busca.focus();
    };

    const mostrarAviso = (texto) => {
        aviso.textContent = texto;
        aviso.classList.toggle("hidden", !texto);
    };

    const botaoResultado = (classes, texto, aoClicar) => {
        const botao = elemento("button", classes, texto);
        botao.type = "button";
        botao.addEventListener("click", aoClicar);
        return botao;
    };

    const mostrarResultados = (produtos) => {
        resultados.replaceChildren();
        produtos.forEach((produto) => {
            const linha = elemento("li", "flex flex-wrap items-center gap-2 rounded-box bg-base-200 p-2");
            const dados = elemento("div", "min-w-40 flex-1");
            dados.append(elemento("p", "font-medium", produto.nome));
            dados.append(elemento(
                "p",
                "text-sm opacity-70",
                `${moeda.format(Number(produto.preco))} · Estoque: ${produto.saldo}`
            ));
            linha.append(dados);
            linha.append(botaoResultado("btn btn-primary btn-sm", "Unidade", () => adicionar(produto)));
            produto.embalagens.forEach((embalagem) => {
                linha.append(botaoResultado(
                    "btn btn-sm",
                    `${embalagem.tipo} (${embalagem.fator})`,
                    () => adicionar(produto, embalagem)
                ));
            });
            resultados.append(linha);
        });
    };

    const buscar = async (termo) => {
        const numero = ++ultimaBusca;
        const resposta = await fetch(`${form.dataset.urlBusca}?q=${encodeURIComponent(termo)}`);
        const dados = await resposta.json();
        return numero === ultimaBusca ? dados : null;
    };

    busca.addEventListener("input", () => {
        clearTimeout(temporizador);
        const termo = busca.value.trim();
        if (!termo) {
            ultimaBusca += 1;
            resultados.replaceChildren();
            mostrarAviso("");
            return;
        }
        temporizador = setTimeout(async () => {
            const dados = await buscar(termo);
            if (dados) {
                mostrarResultados(dados.resultados);
                mostrarAviso(dados.resultados.length ? "" : "Nenhum produto encontrado.");
            }
        }, 200);
    });

    // O leitor de código de barras digita o código e envia Enter.
    busca.addEventListener("keydown", async (evento) => {
        if (evento.key !== "Enter") {
            return;
        }
        evento.preventDefault();
        clearTimeout(temporizador);
        const termo = busca.value.trim();
        if (!termo) {
            return;
        }
        const dados = await buscar(termo);
        if (!dados) {
            return;
        }
        if (dados.exato || dados.resultados.length === 1) {
            const produto = dados.resultados[0];
            const embalagem = produto.embalagens.find((opcao) => opcao.id === dados.embalagem);
            adicionar(produto, embalagem);
        } else {
            mostrarResultados(dados.resultados);
            mostrarAviso(dados.resultados.length ? "" : "Nenhum produto encontrado.");
        }
    });

    form.addEventListener("keydown", (evento) => {
        if (evento.key === "Enter" && evento.target.tagName === "INPUT") {
            evento.preventDefault();
        }
    });
    form.elements.desconto.addEventListener("input", atualizarResumo);
    form.addEventListener("submit", () => {
        atualizarResumo();
        form.querySelector('button[type="submit"]').disabled = true;
    });

    desenhar();
})();
