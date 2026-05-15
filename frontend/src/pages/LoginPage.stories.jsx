import { MemoryRouter } from "react-router-dom";
import LoginPage from "./LoginPage";

export default {
  title: "Pages/LoginPage",
  component: LoginPage,
  decorators: [
    (Story) => (
      <MemoryRouter>
        <Story />
      </MemoryRouter>
    ),
  ],
};

export const Default = {};
