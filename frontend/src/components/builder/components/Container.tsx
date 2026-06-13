"use client";

import React from "react";
import { useNode } from "@craftjs/core";
import { Slider } from "@/components/ui/slider";
import { Label } from "@/components/ui/label";

interface ContainerProps {
  background?: string;
  padding?: number;
  children?: React.ReactNode;
}

export const Container = ({ background, padding = 0, children }: ContainerProps) => {
  const { connectors: { connect, drag } } = useNode();

  return (
    <div
      ref={(ref: any) => connect(drag(ref))}
      style={{ background, padding: `${padding}px` }}
      className="border border-dashed border-muted-foreground/30 min-h-[50px] rounded-md"
    >
      {children}
    </div>
  );
};

const ContainerSettings = () => {
  const { padding, actions: { setProp } } = useNode((node) => ({
    padding: node.data.props.padding
  }));

  return (
    <div className="space-y-4">
      <div className="space-y-2">
        <Label>Padding</Label>
        <Slider 
          defaultValue={[padding]} 
          max={100} 
          step={1} 
          onValueChange={(val) => setProp((props: any) => props.padding = val[0])} 
        />
      </div>
    </div>
  );
}

Container.craft = {
  props: {
    background: 'transparent',
    padding: 20
  },
  related: {
    settings: ContainerSettings
  }
};
