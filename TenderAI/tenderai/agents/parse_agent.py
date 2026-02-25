from llama_parse import LlamaParse


class ParseAgent:
    def __init__(self, llama_cloud_api_key: str):
        self.api_key = llama_cloud_api_key

    def _parser(self) -> LlamaParse:
        """Build a fresh parser per call to avoid closed TCPTransport/handler in long-lived clients."""
        return LlamaParse(
            api_key=self.api_key,
            result_type="markdown",
            verbose=False,
        )

    def parse_file(self, file_path: str) -> str:
        parser = self._parser()
        try:
            docs = parser.load_data(file_path)
        except Exception as e:
            msg = str(e)
            if "TCPTransport closed" in msg or "handler is closed" in msg:
                # Retry once with a brand-new parser (no reused connection)
                parser = self._parser()
                docs = parser.load_data(file_path)
            else:
                raise
        return "\n\n".join(getattr(d, "text", str(d)) for d in docs)
