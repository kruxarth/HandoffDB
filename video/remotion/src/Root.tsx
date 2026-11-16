import React from "react";
import { Composition, Folder } from "remotion";
import { Main, SCENES } from "./Main";
import { timeline } from "./ui";

export const RemotionRoot: React.FC = () => (
  <>
    <Composition id="BearingsLaunch" component={Main} width={1920} height={1080} fps={timeline.fps} durationInFrames={timeline.frames} />
    <Folder name="Scenes">
      {timeline.scenes.map((sc) => {
        const Comp = SCENES[sc.name];
        const Wrapped: React.FC = () => <Comp sc={sc} />;
        return <Composition key={sc.name} id={`scene-${sc.name}`} component={Wrapped} width={1920} height={1080} fps={timeline.fps} durationInFrames={sc.frames} />;
      })}
    </Folder>
  </>
);
