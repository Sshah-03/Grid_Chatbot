import type { LinkPreview } from "../types";
import { getHostname } from "../utils/links";

type LinkPreviewCardProps = {
  preview: LinkPreview;
};

export function LinkPreviewCard({ preview }: LinkPreviewCardProps) {
  return (
    <a className="link-preview" href={preview.url} rel="noreferrer" target="_blank">
      {preview.image_url && <img src={preview.image_url} alt="" />}
      <span>
        <strong>{preview.title || preview.url}</strong>
        {preview.description && <small>{preview.description}</small>}
        <em>{preview.site_name || getHostname(preview.url)}</em>
      </span>
    </a>
  );
}
