import { MemoryRouter } from "react-router-dom";
import Header from "./Header";

export default {
  title: "Components/Layout/Header",
  component: Header,
  decorators: [
    (Story) => (
      <MemoryRouter>
        <Story />
      </MemoryRouter>
    ),
  ],
};

export const Default = {};
