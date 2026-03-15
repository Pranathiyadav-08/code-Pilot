import ReactMarkdown from "react-markdown";
import remarkGfm from "remark-gfm";

function ChatResponse({ answer }) {
  return (
    <div className="response">
      <ReactMarkdown remarkPlugins={[remarkGfm]}>
        {answer}
      </ReactMarkdown>
    </div>
  );
}

export default ChatResponse;
