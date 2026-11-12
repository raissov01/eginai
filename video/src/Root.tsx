import { Composition } from "remotion";
import { Video, TOTAL } from "./Video";
import "./fonts";

export const RemotionRoot: React.FC = () => (
  <Composition id="EginAI" component={Video} durationInFrames={TOTAL} fps={30} width={1920} height={1080} />
);
