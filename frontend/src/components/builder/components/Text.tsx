"use client";

import React from "react";
import { useNode } from "@craftjs/core";
import { Input } from "@/components/ui/input";
import { Label } from "@/components/ui/label";

interface TextProps {
  text: string;
  fontSize: number;
}

export const Text = ({ text, fontSize }: TextProps) => {
  const { connectors: { connect, drag } } = useNode();

  return (
    <div ref={(ref: any) => connect(drag(ref))} style={{ fontSize: `${fontSize}px` }}>
      {text}
    </div>
  );
};

const TextSettings = () => {
  const { actions: { setProp }, text, fontSize } = useNode((node) => ({
    text: node.data.props.text,
    fontSize: node.data.props.fontSize
  }));

  return (
    <div className="space-y-4">
      <div className="space-y-2">
        <Label>Texto</Label>
        <Input 
          defaultValue={text} 
          onChange={(e) => setProp((props: any) => props.text = e.target.value)} 
        />
      </div>
      <div className="space-y-2">
        <Label>Tamaño de fuente</Label>
        <Input 
          type="number"
          defaultValue={fontSize} 
          onChange={(e) => setProp((props: any) => props.fontSize = parseInt(e.target.value))} 
        />
      </div>
    </div>
  );
};

Text.craft = {
  props: {
    text: "Texto",
    fontSize: 16
  },
  related: {
    settings: TextSettings
  }
};
